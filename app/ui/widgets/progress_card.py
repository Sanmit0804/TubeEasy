import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame
)
from app.utils.formatting import format_bytes, format_speed, format_eta

class ProgressCard(QFrame):
    """
    Minimalist card widget showing live download progress, speed, ETA, status,
    and post-download action buttons.
    """
    cancel_clicked = Signal()
    retry_clicked = Signal()
    download_again_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self._current_filepath: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header row: Status label + Cancel button
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Ready", self)
        self.status_label.setObjectName("SectionTitle")
        self.status_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
        header_layout.addWidget(self.cancel_btn)

        layout.addLayout(header_layout)

        # Progress bar (modern flat bar)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Metrics row: Size (Downloaded / Total), Speed, ETA
        metrics_layout = QHBoxLayout()
        
        self.size_label = QLabel("0 MB / 0 MB", self)
        self.size_label.setObjectName("SubtitleLabel")
        metrics_layout.addWidget(self.size_label)

        metrics_layout.addStretch()

        self.speed_label = QLabel("-- MB/s", self)
        self.speed_label.setObjectName("SubtitleLabel")
        metrics_layout.addWidget(self.speed_label)

        metrics_layout.addStretch()

        self.eta_label = QLabel("--:-- remaining", self)
        self.eta_label.setObjectName("SubtitleLabel")
        metrics_layout.addWidget(self.eta_label)

        layout.addLayout(metrics_layout)

        # Completion Action Bar (Hidden by default)
        self.actions_widget = QWidget(self)
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 4, 0, 0)
        actions_layout.setSpacing(8)

        self.success_label = QLabel("Download complete", self.actions_widget)
        self.success_label.setStyleSheet("color: #34D399; font-weight: 600; font-size: 13px;")
        actions_layout.addWidget(self.success_label)

        actions_layout.addStretch()

        self.open_file_btn = QPushButton("Open File", self.actions_widget)
        self.open_file_btn.setObjectName("SecondaryButton")
        self.open_file_btn.setCursor(Qt.PointingHandCursor)
        self.open_file_btn.clicked.connect(self._open_file)
        actions_layout.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("Open Folder", self.actions_widget)
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._open_folder)
        actions_layout.addWidget(self.open_folder_btn)

        self.again_btn = QPushButton("Download Another", self.actions_widget)
        self.again_btn.setObjectName("SecondaryButton")
        self.again_btn.setCursor(Qt.PointingHandCursor)
        self.again_btn.clicked.connect(self.download_again_clicked.emit)
        actions_layout.addWidget(self.again_btn)

        self.actions_widget.setVisible(False)
        layout.addWidget(self.actions_widget)

    def update_progress(self, data: dict):
        """Update metrics from DownloadWorker progress hook dict."""
        pct = data.get("percentage", 0.0)
        self.progress_bar.setValue(int(pct))
        
        downloaded = data.get("downloaded_bytes", 0)
        total = data.get("total_bytes", 0)
        if total > 0:
            self.size_label.setText(f"{format_bytes(downloaded)} / {format_bytes(total)}")
        elif downloaded > 0:
            self.size_label.setText(f"{format_bytes(downloaded)}")
        else:
            self.size_label.setText("-- / --")

        speed = data.get("speed", 0)
        self.speed_label.setText(format_speed(speed))

        eta = data.get("eta", 0)
        self.eta_label.setText(f"{format_eta(eta)} remaining" if eta else "--:-- remaining")

        status = data.get("status", "")
        if status:
            self.status_label.setText(status)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def show_downloading(self):
        self.actions_widget.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.size_label.setText("Preparing...")
        self.speed_label.setText("-- MB/s")
        self.eta_label.setText("--:--")
        self.status_label.setText("Starting download...")
        self.setVisible(True)

    def show_completed(self, filepath: str):
        self._current_filepath = filepath
        self.cancel_btn.setVisible(False)
        self.actions_widget.setVisible(True)
        self.status_label.setText("Completed")
        self.progress_bar.setValue(100)
        if os.path.exists(filepath):
            sz = os.path.getsize(filepath)
            self.size_label.setText(f"File size: {format_bytes(sz)}")
        self.speed_label.setText("")
        self.eta_label.setText("")

    def show_failed(self, error_msg: str):
        self.cancel_btn.setVisible(False)
        self.actions_widget.setVisible(False)
        self.status_label.setText(f"Failed: {error_msg}")
        self.status_label.setStyleSheet("color: #F87171; font-weight: 600;")

    def show_cancelled(self):
        self.cancel_btn.setVisible(False)
        self.actions_widget.setVisible(False)
        self.status_label.setText("Download cancelled.")
        self.speed_label.setText("")
        self.eta_label.setText("")

    def _open_file(self):
        if self._current_filepath and os.path.exists(self._current_filepath):
            if sys.platform == "win32":
                os.startfile(self._current_filepath)
            else:
                subprocess.Popen(["xdg-open", self._current_filepath])

    def _open_folder(self):
        if self._current_filepath:
            folder = os.path.dirname(self._current_filepath)
            if os.path.exists(folder):
                if sys.platform == "win32":
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(self._current_filepath)}"')
                else:
                    subprocess.Popen(["xdg-open", folder])