import os
import sys
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QScrollArea,
    QApplication
)
from app.models.video_info import VideoInfo, FormatOption
from app.models.playlist_info import PlaylistInfo
from app.downloader.ytdlp_manager import YtDlpManager, YtDlpException
from app.downloader.download_worker import DownloadWorker
from app.downloader.ffmpeg_manager import FFmpegManager
from app.config.settings import SettingsManager
from app.utils.url_validator import is_valid_youtube_url, is_playlist_url, clean_youtube_url
from app.utils.path_utils import get_resource_path
from app.ui.widgets.thumbnail_loader import ThumbnailWidget
from app.ui.widgets.preset_bar import PresetBar
from app.ui.widgets.format_table import FormatTableWidget
from app.ui.widgets.progress_card import ProgressCard
from app.ui.settings_dialog import SettingsDialog
from app.ui.playlist_dialog import PlaylistPromptDialog, PlaylistManagerDialog
from app.services.logger import get_logger

logger = get_logger("MainWindow")

class AnalyzeWorker(QThread):
    finished_video = Signal(object)      # VideoInfo
    finished_playlist = Signal(object)   # PlaylistInfo
    error = Signal(str)

    def __init__(self, url: str, is_playlist: bool = False, parent=None):
        super().__init__(parent)
        self.url = url
        self.is_playlist = is_playlist

    def run(self):
        try:
            if self.is_playlist:
                info = YtDlpManager.extract_playlist_info(self.url)
                self.finished_playlist.emit(info)
            else:
                info = YtDlpManager.extract_video_info(self.url)
                self.finished_video.emit(info)
        except YtDlpException as e:
            self.error.emit(str(e))
        except Exception as e:
            logger.error("Analyze worker exception: %s", str(e), exc_info=True)
            self.error.emit(f"Failed to analyze video: {str(e)}")

class MainWindow(QMainWindow):
    """Primary application window for TubeEasy."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TubeEasy")
        self.setMinimumSize(900, 660)
        self.resize(960, 720)

        self.settings_mgr = SettingsManager.get_instance()
        self.current_video_info: Optional[VideoInfo] = None
        self.analyze_worker: Optional[AnalyzeWorker] = None
        self.download_worker: Optional[DownloadWorker] = None

        self._init_ui()
        self._load_app_icon()
        self._apply_theme(self.settings_mgr.settings.theme)
        self._check_ffmpeg_status()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Modern Minimal Header Bar
        header_bar = QFrame(self)
        header_bar.setObjectName("HeaderBar")
        header_bar_layout = QHBoxLayout(header_bar)
        header_bar_layout.setContentsMargins(20, 10, 20, 10)
        header_bar_layout.setSpacing(12)

        # Title
        app_title = QLabel("TubeEasy", header_bar)
        app_title.setObjectName("TitleLabel")
        header_bar_layout.addWidget(app_title)

        # Minimal status badge for FFmpeg
        self.ffmpeg_badge = QLabel("FFmpeg: Checking...", header_bar)
        self.ffmpeg_badge.setObjectName("BadgeLabel")
        header_bar_layout.addWidget(self.ffmpeg_badge)

        header_bar_layout.addStretch()

        # Settings Button
        self.settings_btn = QPushButton("Settings", header_bar)
        self.settings_btn.setObjectName("SecondaryButton")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self._open_settings)
        header_bar_layout.addWidget(self.settings_btn)

        root_layout.addWidget(header_bar)

        # Scrollable content area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        self.main_layout = QVBoxLayout(content_widget)
        self.main_layout.setContentsMargins(22, 18, 22, 18)
        self.main_layout.setSpacing(14)

        # 2. URL Input Card
        url_card = QFrame(content_widget)
        url_card.setObjectName("CardFrame")
        url_layout = QVBoxLayout(url_card)
        url_layout.setContentsMargins(16, 14, 16, 14)
        url_layout.setSpacing(8)

        url_title = QLabel("Video or Playlist URL", url_card)
        url_title.setObjectName("SectionTitle")
        url_layout.addWidget(url_title)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.url_input = QLineEdit(url_card)
        self.url_input.setPlaceholderText("Paste YouTube link here...")
        self.url_input.returnPressed.connect(self._on_analyze_clicked)
        if self.settings_mgr.settings.remember_url and self.settings_mgr.settings.last_url:
            self.url_input.setText(self.settings_mgr.settings.last_url)
        input_row.addWidget(self.url_input)

        paste_btn = QPushButton("Paste", url_card)
        paste_btn.setObjectName("SecondaryButton")
        paste_btn.setCursor(Qt.PointingHandCursor)
        paste_btn.clicked.connect(self._on_paste_clicked)
        input_row.addWidget(paste_btn)

        self.analyze_btn = QPushButton("Analyze", url_card)
        self.analyze_btn.setObjectName("PrimaryButton")
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        input_row.addWidget(self.analyze_btn)

        url_layout.addLayout(input_row)
        self.main_layout.addWidget(url_card)

        # 3. Video Metadata Card (Initially hidden)
        self.meta_card = QFrame(content_widget)
        self.meta_card.setObjectName("CardFrame")
        meta_layout = QHBoxLayout(self.meta_card)
        meta_layout.setContentsMargins(14, 12, 14, 12)
        meta_layout.setSpacing(16)

        self.thumbnail_widget = ThumbnailWidget(220, 124, self.meta_card)
        meta_layout.addWidget(self.thumbnail_widget)

        meta_info_layout = QVBoxLayout()
        meta_info_layout.setSpacing(5)

        self.video_title_lbl = QLabel("Video Title", self.meta_card)
        self.video_title_lbl.setObjectName("TitleLabel")
        self.video_title_lbl.setWordWrap(True)
        self.video_title_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        meta_info_layout.addWidget(self.video_title_lbl)

        self.channel_lbl = QLabel("Channel: Unknown", self.meta_card)
        self.channel_lbl.setObjectName("SubtitleLabel")
        meta_info_layout.addWidget(self.channel_lbl)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        
        self.duration_badge = QLabel("Duration: --", self.meta_card)
        self.duration_badge.setObjectName("BadgeLabel")
        badges_row.addWidget(self.duration_badge)

        self.views_badge = QLabel("Views: --", self.meta_card)
        self.views_badge.setObjectName("BadgeLabel")
        badges_row.addWidget(self.views_badge)

        badges_row.addStretch()
        meta_info_layout.addLayout(badges_row)

        meta_info_layout.addStretch()
        meta_layout.addLayout(meta_info_layout)

        self.meta_card.setVisible(False)
        self.main_layout.addWidget(self.meta_card)

        # 4. Formats Section (Initially hidden)
        self.formats_container = QFrame(content_widget)
        self.formats_container.setObjectName("CardFrame")
        formats_layout = QVBoxLayout(self.formats_container)
        formats_layout.setContentsMargins(14, 12, 14, 12)
        formats_layout.setSpacing(8)

        formats_title = QLabel("Available Formats", self.formats_container)
        formats_title.setObjectName("SectionTitle")
        formats_layout.addWidget(formats_title)

        # Preset bar
        self.preset_bar = PresetBar(self.formats_container)
        self.preset_bar.preset_selected.connect(self._on_preset_selected)
        formats_layout.addWidget(self.preset_bar)

        # Table
        self.format_table = FormatTableWidget(self.formats_container)
        self.format_table.format_selected.connect(self._on_format_selected)
        formats_layout.addWidget(self.format_table)

        self.formats_container.setVisible(False)
        self.main_layout.addWidget(self.formats_container)

        # 5. Output Folder & Download Action Row (Initially hidden)
        self.download_row = QFrame(content_widget)
        self.download_row.setObjectName("CardFrame")
        dl_layout = QHBoxLayout(self.download_row)
        dl_layout.setContentsMargins(14, 12, 14, 12)
        dl_layout.setSpacing(10)

        dl_lbl = QLabel("Save to:", self.download_row)
        dl_lbl.setObjectName("SubtitleLabel")
        dl_layout.addWidget(dl_lbl)

        self.dest_input = QLineEdit(self.download_row)
        self.dest_input.setText(self.settings_mgr.settings.download_dir)
        dl_layout.addWidget(self.dest_input)

        browse_btn = QPushButton("Browse...", self.download_row)
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse_dest)
        dl_layout.addWidget(browse_btn)

        self.start_download_btn = QPushButton("Download", self.download_row)
        self.start_download_btn.setObjectName("PrimaryButton")
        self.start_download_btn.setCursor(Qt.PointingHandCursor)
        self.start_download_btn.clicked.connect(self._on_start_download_clicked)
        dl_layout.addWidget(self.start_download_btn)

        self.download_row.setVisible(False)
        self.main_layout.addWidget(self.download_row)

        # 6. Progress Card (Initially hidden)
        self.progress_card = ProgressCard(content_widget)
        self.progress_card.cancel_clicked.connect(self._on_cancel_download)
        self.progress_card.download_again_clicked.connect(self._on_download_again)
        self.progress_card.setVisible(False)
        self.main_layout.addWidget(self.progress_card)

        self.main_layout.addStretch()

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def _load_app_icon(self):
        icon_path = get_resource_path("assets/app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _apply_theme(self, theme_name: str):
        if theme_name == "light":
            qss_path = get_resource_path("app/ui/styles/light.qss")
        else:
            qss_path = get_resource_path("app/ui/styles/dark.qss")

        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _check_ffmpeg_status(self):
        if FFmpegManager.is_available():
            self.ffmpeg_badge.setText("FFmpeg Ready")
            self.ffmpeg_badge.setStyleSheet("color: #34D399; font-weight: 500; font-size: 11px;")
        else:
            self.ffmpeg_badge.setText("FFmpeg Missing")
            self.ffmpeg_badge.setStyleSheet("color: #F87171; font-weight: 500; font-size: 11px;")

    def _on_paste_clicked(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)
            if is_valid_youtube_url(text):
                self._on_analyze_clicked()

    def _on_analyze_clicked(self):
        raw_url = self.url_input.text().strip()
        if not raw_url:
            QMessageBox.warning(self, "Missing URL", "Please enter or paste a YouTube URL.")
            return

        if not is_valid_youtube_url(raw_url):
            QMessageBox.critical(
                self,
                "Invalid URL",
                "The entered URL is not a recognized YouTube video or playlist link.\n\n"
                "Please enter a valid link, e.g.:\n"
                "• https://www.youtube.com/watch?v=...\n"
                "• https://youtu.be/...\n"
                "• https://www.youtube.com/shorts/..."
            )
            return

        url = clean_youtube_url(raw_url)
        
        # Save last URL if enabled
        if self.settings_mgr.settings.remember_url:
            self.settings_mgr.update(last_url=url)

        # Check if playlist
        if is_playlist_url(url):
            self._handle_playlist_analysis(url)
            return

        # Start Single Video Analysis
        self._start_video_analysis(url)

    def _start_video_analysis(self, url: str):
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        self.meta_card.setVisible(False)
        self.formats_container.setVisible(False)
        self.download_row.setVisible(False)
        self.progress_card.setVisible(False)

        self.analyze_worker = AnalyzeWorker(url, is_playlist=False, parent=self)
        self.analyze_worker.finished_video.connect(self._on_video_analyzed)
        self.analyze_worker.error.connect(self._on_analyze_error)
        self.analyze_worker.start()

    def _handle_playlist_analysis(self, url: str):
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Inspecting...")

        self.analyze_worker = AnalyzeWorker(url, is_playlist=True, parent=self)
        self.analyze_worker.finished_playlist.connect(self._on_playlist_analyzed)
        self.analyze_worker.error.connect(self._on_analyze_error)
        self.analyze_worker.start()

    def _on_playlist_analyzed(self, p_info: PlaylistInfo):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")

        prompt = PlaylistPromptDialog(p_info, self)
        prompt.exec()

        if prompt.choice == PlaylistPromptDialog.CHOICE_SINGLE:
            # Analyze single video
            self._start_video_analysis(p_info.url)
        elif prompt.choice == PlaylistPromptDialog.CHOICE_PLAYLIST:
            mgr = PlaylistManagerDialog(p_info, self)
            mgr.exec()

    def _on_video_analyzed(self, info: VideoInfo):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        self.current_video_info = info

        # Populate Metadata Card
        self.video_title_lbl.setText(info.title)
        self.channel_lbl.setText(f"Channel: {info.channel}")
        self.duration_badge.setText(f"Duration: {info.duration_formatted}")
        self.views_badge.setText(info.views_formatted)
        self.thumbnail_widget.load_from_url(info.thumbnail_url, info.duration_formatted)
        self.meta_card.setVisible(True)

        # Populate Formats Table
        self.format_table.set_formats(info.formats)
        self.formats_container.setVisible(True)

        # Show Download row
        self.dest_input.setText(self.settings_mgr.settings.download_dir)
        self.download_row.setVisible(True)

    def _on_analyze_error(self, err_msg: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"Unable to analyze this video.\n\n{err_msg}\n\n"
            "Please verify that the video is public, accessible, and not age-restricted."
        )

    def _on_preset_selected(self, preset_key: str):
        self.preset_bar.set_active_preset(preset_key)
        self.format_table.select_preset(preset_key)

    def _on_format_selected(self, fmt: FormatOption):
        pass

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.dest_input.text())
        if folder:
            self.dest_input.setText(folder)
            self.settings_mgr.update(download_dir=folder)

    def _on_start_download_clicked(self):
        if not self.current_video_info:
            return

        selected_fmt = self.format_table.get_selected_format()
        if not selected_fmt:
            QMessageBox.warning(self, "No Format Selected", "Please select a download format from the table.")
            return

        dest_dir = self.dest_input.text().strip()
        if not dest_dir:
            QMessageBox.warning(self, "Invalid Directory", "Please specify a valid destination folder.")
            return

        os.makedirs(dest_dir, exist_ok=True)
        self.settings_mgr.update(download_dir=dest_dir)

        # Disable download controls during download
        self.start_download_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress_card.show_downloading()

        # Start Download Worker
        self.download_worker = DownloadWorker(
            video_info=self.current_video_info,
            format_option=selected_fmt,
            output_dir=dest_dir,
            parent=self
        )
        self.download_worker.progress_signal.connect(self.progress_card.update_progress)
        self.download_worker.status_signal.connect(self.progress_card.set_status)
        self.download_worker.finished_signal.connect(self._on_download_finished)
        self.download_worker.error_signal.connect(self._on_download_error)
        self.download_worker.cancelled_signal.connect(self._on_download_cancelled)
        self.download_worker.start()

    def _on_download_finished(self, filepath: str):
        self.start_download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.progress_card.show_completed(filepath)

        if self.settings_mgr.settings.auto_open_folder:
            folder = os.path.dirname(filepath)
            if sys.platform == "win32":
                os.startfile(folder)

    def _on_download_error(self, err_msg: str):
        self.start_download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.progress_card.show_failed(err_msg)
        QMessageBox.critical(self, "Download Error", f"Download encountered an error:\n\n{err_msg}")

    def _on_download_cancelled(self):
        self.start_download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.progress_card.show_cancelled()

    def _on_cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()

    def _on_download_again(self):
        self.progress_card.setVisible(False)
        self.url_input.setFocus()
        self.url_input.selectAll()

    def _open_settings(self):
        dialog = SettingsDialog(self)
        dialog.theme_changed.connect(self._apply_theme)
        dialog.exec()
        self.dest_input.setText(self.settings_mgr.settings.download_dir)

    def closeEvent(self, event):
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Download in Progress",
                "A download is currently in progress. Are you sure you want to cancel and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_worker.cancel()
                self.download_worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()