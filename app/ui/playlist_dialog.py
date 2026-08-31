import os
from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QCheckBox, QProgressBar, QFrame, QComboBox, QMessageBox
)
from app.models.playlist_info import PlaylistInfo, PlaylistItem
from app.models.video_info import FormatOption, VideoInfo
from app.downloader.download_worker import DownloadWorker
from app.downloader.ytdlp_manager import YtDlpManager
from app.config.settings import SettingsManager
from app.services.logger import get_logger

logger = get_logger("PlaylistDialog")

class PlaylistBatchThread(QThread):
    item_progress = Signal(int, dict)       # item_index, progress_dict
    item_finished = Signal(int, str)        # item_index, filepath
    item_error = Signal(int, str)           # item_index, error_msg
    overall_progress = Signal(int, int)     # completed_count, total_count
    all_finished = Signal()

    def __init__(self, items: List[PlaylistItem], format_key: str, output_dir: str, parent=None):
        super().__init__(parent)
        self.items = items
        self.format_key = format_key
        self.output_dir = output_dir
        self._is_cancelled = False
        self._current_worker: Optional[DownloadWorker] = None

    def cancel(self):
        self._is_cancelled = True
        if self._current_worker:
            self._current_worker.cancel()

    def run(self):
        completed = 0
        total = len(self.items)
        self.overall_progress.emit(0, total)

        for item in self.items:
            if self._is_cancelled:
                break
                
            try:
                # Fetch video info for item
                v_info = YtDlpManager.extract_video_info(item.url)
                
                # Determine format option
                fmt_opt = None
                if self.format_key == "best":
                    va = [f for f in v_info.formats if f.format_type == "video_audio"]
                    fmt_opt = va[0] if va else v_info.formats[0]
                elif self.format_key == "1080p":
                    c = [f for f in v_info.formats if f.format_type == "video_audio" and f.height == 1080]
                    fmt_opt = c[0] if c else (v_info.formats[0])
                elif self.format_key == "720p":
                    c = [f for f in v_info.formats if f.format_type == "video_audio" and f.height == 720]
                    fmt_opt = c[0] if c else (v_info.formats[0])
                elif self.format_key == "mp3":
                    c = [f for f in v_info.formats if f.format_type == "audio_only" and f.container == "mp3"]
                    fmt_opt = c[0] if c else (v_info.formats[0])
                else:
                    fmt_opt = v_info.formats[0]

                # Run worker synchronously in this thread
                worker = DownloadWorker(v_info, fmt_opt, self.output_dir)
                self._current_worker = worker
                
                def on_prog(d):
                    self.item_progress.emit(item.index, d)
                    
                worker.progress_signal.connect(on_prog)
                worker.run()
                
                if worker._final_filepath and os.path.exists(worker._final_filepath):
                    self.item_finished.emit(item.index, worker._final_filepath)
                    completed += 1
                else:
                    self.item_error.emit(item.index, "File not found after download.")
                    
            except Exception as e:
                self.item_error.emit(item.index, str(e))
                
            self.overall_progress.emit(completed, total)

        self.all_finished.emit()

class PlaylistPromptDialog(QDialog):
    """Initial choice prompt when a playlist URL is pasted."""
    CHOICE_SINGLE = 1
    CHOICE_PLAYLIST = 2
    CHOICE_CANCEL = 0

    def __init__(self, playlist_info: PlaylistInfo, parent=None):
        super().__init__(parent)
        self.playlist_info = playlist_info
        self.choice = self.CHOICE_CANCEL
        self.setWindowTitle("Playlist Detected")
        self.setFixedWidth(460)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_lbl = QLabel(f"<b>Playlist:</b> {self.playlist_info.title}", self)
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        info_lbl = QLabel(
            f"This URL points to a playlist containing <b>{self.playlist_info.item_count}</b> videos.<br>"
            "How would you like to proceed?",
            self
        )
        info_lbl.setTextFormat(Qt.RichText)
        layout.addWidget(info_lbl)

        # Choices
        self.single_btn = QPushButton("Download This Single Video", self)
        self.single_btn.setObjectName("SecondaryButton")
        self.single_btn.clicked.connect(self._select_single)
        layout.addWidget(self.single_btn)

        self.playlist_btn = QPushButton("Download Entire Playlist / Select Videos", self)
        self.playlist_btn.setObjectName("PrimaryButton")
        self.playlist_btn.clicked.connect(self._select_playlist)
        layout.addWidget(self.playlist_btn)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

    def _select_single(self):
        self.choice = self.CHOICE_SINGLE
        self.accept()

    def _select_playlist(self):
        self.choice = self.CHOICE_PLAYLIST
        self.accept()

class PlaylistManagerDialog(QDialog):
    """Full playlist download manager with item selection and batch progress."""
    def __init__(self, playlist_info: PlaylistInfo, parent=None):
        super().__init__(parent)
        self.playlist_info = playlist_info
        self.setWindowTitle(f"Playlist: {self.playlist_info.title}")
        self.resize(680, 520)
        self._batch_thread: Optional[PlaylistBatchThread] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header info
        hdr_layout = QHBoxLayout()
        title_lbl = QLabel(f"<b>{self.playlist_info.title}</b> ({len(self.playlist_info.items)} videos)", self)
        title_lbl.setObjectName("SectionTitle")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()

        layout.addLayout(hdr_layout)

        # Selection buttons
        sel_layout = QHBoxLayout()
        sel_all_btn = QPushButton("Select All", self)
        sel_all_btn.setObjectName("SecondaryButton")
        sel_all_btn.clicked.connect(self._select_all)
        sel_layout.addWidget(sel_all_btn)

        desel_all_btn = QPushButton("Deselect All", self)
        desel_all_btn.setObjectName("SecondaryButton")
        desel_all_btn.clicked.connect(self._deselect_all)
        sel_layout.addWidget(desel_all_btn)

        sel_layout.addStretch()

        format_lbl = QLabel("Format:", self)
        sel_layout.addWidget(format_lbl)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["Best Video Quality", "1080p Full HD", "720p HD", "MP3 Audio Only"])
        sel_layout.addWidget(self.format_combo)

        layout.addLayout(sel_layout)

        # List of items
        self.list_widget = QListWidget(self)
        self.list_widget.setAlternatingRowColors(True)
        for item in self.playlist_info.items:
            list_item = QListWidgetItem(self.list_widget)
            list_item.setText(f"[{item.index}] {item.title} ({item.duration_formatted})")
            list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
            list_item.setCheckState(Qt.Checked if item.selected else Qt.Unchecked)
        layout.addWidget(self.list_widget)

        # Overall Progress
        self.overall_label = QLabel("Ready to download", self)
        self.overall_label.setObjectName("SubtitleLabel")
        layout.addWidget(self.overall_label)

        self.overall_bar = QProgressBar(self)
        self.overall_bar.setRange(0, len(self.playlist_info.items))
        self.overall_bar.setValue(0)
        layout.addWidget(self.overall_bar)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Close", self)
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self._on_close)
        btn_layout.addWidget(self.cancel_btn)

        self.start_btn = QPushButton("Start Download", self)
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self._start_batch_download)
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)

    def _start_batch_download(self):
        selected_items: List[PlaylistItem] = []
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).checkState() == Qt.Checked:
                selected_items.append(self.playlist_info.items[i])

        if not selected_items:
            QMessageBox.warning(self, "No Videos Selected", "Please select at least one video to download.")
            return

        fmt_map = {0: "best", 1: "1080p", 2: "720p", 3: "mp3"}
        fmt_key = fmt_map.get(self.format_combo.currentIndex(), "best")
        out_dir = SettingsManager.get_instance().settings.download_dir

        self.start_btn.setEnabled(False)
        self.cancel_btn.setText("Cancel Downloads")
        self.overall_bar.setRange(0, len(selected_items))
        self.overall_bar.setValue(0)
        self.overall_label.setText(f"Downloading 0 of {len(selected_items)} videos...")

        self._batch_thread = PlaylistBatchThread(selected_items, fmt_key, out_dir, self)
        self._batch_thread.overall_progress.connect(self._on_overall_progress)
        self._batch_thread.all_finished.connect(self._on_all_finished)
        self._batch_thread.start()

    def _on_overall_progress(self, completed: int, total: int):
        self.overall_bar.setValue(completed)
        self.overall_label.setText(f"Completed {completed} of {total} videos...")

    def _on_all_finished(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setText("Close")
        self.overall_label.setText("All downloads finished!")
        QMessageBox.information(self, "Playlist Finished", "Playlist download process completed!")

    def _on_close(self):
        if self._batch_thread and self._batch_thread.isRunning():
            self._batch_thread.cancel()
        self.accept()