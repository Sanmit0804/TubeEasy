from typing import Optional
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

class PresetBar(QWidget):
    """Minimalist horizontal bar of quick-access format presets."""
    preset_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_preset: Optional[str] = None
        self._buttons = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 4)
        main_layout.setSpacing(6)

        title_lbl = QLabel("Presets:", self)
        title_lbl.setObjectName("SubtitleLabel")
        title_lbl.setStyleSheet("font-weight: 500; font-size: 12px;")
        main_layout.addWidget(title_lbl)

        presets = [
            ("Best Quality", "best"),
            ("4K UHD", "4k"),
            ("1440p 2K", "1440p"),
            ("1080p FHD", "1080p"),
            ("720p HD", "720p"),
            ("480p SD", "480p"),
            ("MP3 (320k)", "mp3_320"),
            ("M4A Audio", "m4a"),
        ]

        for label, key in presets:
            btn = QPushButton(label, self)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("padding: 4px 10px; font-size: 11px; border-radius: 4px;")
            btn.clicked.connect(lambda checked=False, k=key: self._on_clicked(k))
            main_layout.addWidget(btn)
            self._buttons[key] = btn

        main_layout.addStretch()

    def _on_clicked(self, key: str):
        self.set_active_preset(key)
        self.preset_selected.emit(key)

    def set_active_preset(self, key: Optional[str]):
        self._active_preset = key
        for k, btn in self._buttons.items():
            if k == key:
                btn.setStyleSheet("padding: 4px 10px; font-size: 11px; border-radius: 4px; background-color: #E11D48; color: #FFFFFF; border: 1px solid #E11D48; font-weight: 600;")
            else:
                btn.setStyleSheet("padding: 4px 10px; font-size: 11px; border-radius: 4px;")