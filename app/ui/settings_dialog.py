import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QLineEdit, QPushButton, QCheckBox, QComboBox, QSpinBox, QFileDialog,
    QMessageBox, QFrame
)
import yt_dlp
from app.config.settings import SettingsManager
from app.downloader.ffmpeg_manager import FFmpegManager

class SettingsDialog(QDialog):
    """Minimalist settings dialog for General, Downloads, Appearance, and About."""
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        self.settings_mgr = SettingsManager.get_instance()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._create_general_tab(), "General")
        self.tabs.addTab(self._create_downloads_tab(), "Downloads")
        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        self.tabs.addTab(self._create_about_tab(), "About")
        layout.addWidget(self.tabs)

        # Bottom action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings", self)
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Default Download Directory:", widget))
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(widget)
        self.dir_input.setText(self.settings_mgr.settings.download_dir)
        dir_layout.addWidget(self.dir_input)

        self.browse_btn = QPushButton("Browse...", widget)
        self.browse_btn.setObjectName("SecondaryButton")
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.browse_btn)
        layout.addLayout(dir_layout)

        self.auto_open_cb = QCheckBox("Automatically open folder after download", widget)
        self.auto_open_cb.setChecked(self.settings_mgr.settings.auto_open_folder)
        layout.addWidget(self.auto_open_cb)

        self.remember_url_cb = QCheckBox("Remember last URL on startup", widget)
        self.remember_url_cb.setChecked(self.settings_mgr.settings.remember_url)
        layout.addWidget(self.remember_url_cb)

        layout.addStretch()
        return widget

    def _create_downloads_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(QLabel("File Collision Handling:", widget))
        self.overwrite_combo = QComboBox(widget)
        self.overwrite_combo.addItems([
            "Automatically rename (e.g. video (1).mp4)",
            "Overwrite existing file",
            "Skip download"
        ])
        mode_map = {"rename": 0, "overwrite": 1, "skip": 2}
        self.overwrite_combo.setCurrentIndex(mode_map.get(self.settings_mgr.settings.overwrite_behavior, 0))
        layout.addWidget(self.overwrite_combo)

        layout.addWidget(QLabel("Preferred Audio Format:", widget))
        self.audio_combo = QComboBox(widget)
        self.audio_combo.addItems(["MP3 (High Quality 320 kbps)", "M4A (Apple AAC)", "WAV (Lossless)", "FLAC (Lossless)"])
        fmt_map = {"mp3": 0, "m4a": 1, "wav": 2, "flac": 3}
        self.audio_combo.setCurrentIndex(fmt_map.get(self.settings_mgr.settings.preferred_audio_format, 0))
        layout.addWidget(self.audio_combo)

        self.metadata_cb = QCheckBox("Embed metadata and cover thumbnail into media files", widget)
        self.metadata_cb.setChecked(self.settings_mgr.settings.embed_metadata)
        layout.addWidget(self.metadata_cb)

        layout.addStretch()
        return widget

    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Color Theme:", widget))
        self.theme_combo = QComboBox(widget)
        self.theme_combo.addItems(["Dark (Minimal Slate)", "Light (Clean Paper)", "System Default"])
        theme_map = {"dark": 0, "light": 1, "system": 2}
        self.theme_combo.setCurrentIndex(theme_map.get(self.settings_mgr.settings.theme, 0))
        layout.addWidget(self.theme_combo)

        info_lbl = QLabel("Theme updates immediately upon saving.", widget)
        info_lbl.setObjectName("SubtitleLabel")
        layout.addWidget(info_lbl)

        layout.addStretch()
        return widget

    def _create_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        app_title = QLabel("YouTube Downloader", widget)
        app_title.setObjectName("TitleLabel")
        layout.addWidget(app_title)

        version_lbl = QLabel("Version 1.0.0 (Standalone Windows Edition)", widget)
        version_lbl.setObjectName("SubtitleLabel")
        layout.addWidget(version_lbl)

        sep = QFrame(widget)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #20242E;")
        layout.addWidget(sep)

        ytdlp_ver = yt_dlp.version.__version__
        ffmpeg_ver = FFmpegManager.get_version()
        
        info_text = (
            f"<b>Engine:</b> yt-dlp {ytdlp_ver}<br>"
            f"<b>FFmpeg:</b> {ffmpeg_ver}<br>"
            f"<b>Platform:</b> 64-bit Windows Executable"
        )
        dep_lbl = QLabel(info_text, widget)
        dep_lbl.setTextFormat(Qt.RichText)
        layout.addWidget(dep_lbl)

        tos_frame = QFrame(widget)
        tos_frame.setObjectName("CardFrame")
        tos_layout = QVBoxLayout(tos_frame)
        tos_layout.setContentsMargins(10, 8, 10, 8)
        
        tos_title = QLabel("Legal & Privacy", tos_frame)
        tos_title.setStyleSheet("font-weight: 600; font-size: 11px;")
        tos_layout.addWidget(tos_title)
        
        tos_text = (
            "• Download content only when permitted by law and rights holders.<br>"
            "• All processing is performed locally on your device with no data collection."
        )
        tos_body = QLabel(tos_text, tos_frame)
        tos_body.setTextFormat(Qt.RichText)
        tos_body.setObjectName("SubtitleLabel")
        tos_body.setStyleSheet("font-size: 11px;")
        tos_layout.addWidget(tos_body)
        
        layout.addWidget(tos_frame)

        layout.addStretch()
        return widget

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.dir_input.text())
        if folder:
            self.dir_input.setText(folder)

    def _save_settings(self):
        new_dir = self.dir_input.text().strip()
        if not new_dir:
            QMessageBox.warning(self, "Invalid Directory", "Please specify a valid download directory.")
            return

        os.makedirs(new_dir, exist_ok=True)

        mode_rev = {0: "rename", 1: "overwrite", 2: "skip"}
        audio_rev = {0: "mp3", 1: "m4a", 2: "wav", 3: "flac"}
        theme_rev = {0: "dark", 1: "light", 2: "system"}

        new_theme = theme_rev.get(self.theme_combo.currentIndex(), "dark")
        old_theme = self.settings_mgr.settings.theme

        self.settings_mgr.update(
            download_dir=new_dir,
            auto_open_folder=self.auto_open_cb.isChecked(),
            remember_url=self.remember_url_cb.isChecked(),
            overwrite_behavior=mode_rev.get(self.overwrite_combo.currentIndex(), "rename"),
            preferred_audio_format=audio_rev.get(self.audio_combo.currentIndex(), "mp3"),
            embed_metadata=self.metadata_cb.isChecked(),
            theme=new_theme
        )

        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        self.accept()