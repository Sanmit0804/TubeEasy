from typing import List, Optional
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QRadioButton, QButtonGroup, QComboBox, QLineEdit, QLabel,
    QAbstractItemView
)
from app.models.video_info import FormatOption

COL_QUALITY = 0
COL_TYPE = 1
COL_CONTAINER = 2
COL_CODEC = 3
COL_FPS = 4
COL_SIZE = 5
COL_AUDIO = 6
COL_SELECT = 7

class FormatTableWidget(QWidget):
    """
    Rich interactive table displaying available download formats with sorting,
    type filtering, and radio button selection.
    """
    format_selected = Signal(object)  # Emits FormatOption

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_formats: List[FormatOption] = []
        self._displayed_formats: List[FormatOption] = []
        self._selected_format: Optional[FormatOption] = None
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Filter header
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        filter_label = QLabel("Filter By:", self)
        filter_label.setObjectName("SubtitleLabel")
        filter_layout.addWidget(filter_label)

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItems(["All Formats", "Video + Audio", "Audio Only", "Video Only"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Quality / Stream", "Type", "Format", "Codec", "FPS", "Est. Size", "Audio", "Select"
        ])
        
        self.table.horizontalHeader().setSectionResizeMode(COL_QUALITY, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_CONTAINER, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_CODEC, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_FPS, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_SIZE, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_AUDIO, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_SELECT, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_SELECT, 65)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.cellClicked.connect(self._on_row_clicked)

        layout.addWidget(self.table)

    def set_formats(self, formats: List[FormatOption]):
        self._all_formats = formats
        self._apply_filter()
        # Default select the first best video+audio format
        self.select_preset("best")

    def _apply_filter(self):
        filter_type = self.filter_combo.currentText()
        
        if filter_type == "Video + Audio":
            self._displayed_formats = [f for f in self._all_formats if f.format_type == "video_audio"]
        elif filter_type == "Audio Only":
            self._displayed_formats = [f for f in self._all_formats if f.format_type == "audio_only"]
        elif filter_type == "Video Only":
            self._displayed_formats = [f for f in self._all_formats if f.format_type == "video_only"]
        else:
            self._displayed_formats = list(self._all_formats)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        # Clear button group
        for btn in self._button_group.buttons():
            self._button_group.removeButton(btn)

        self.table.setRowCount(len(self._displayed_formats))
        
        for row, fmt in enumerate(self._displayed_formats):
            # Quality item
            item_quality = QTableWidgetItem(fmt.resolution)
            item_quality.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
            # Type item
            item_type = QTableWidgetItem(fmt.type_badge)
            item_type.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_type.setTextAlignment(Qt.AlignCenter)
            
            # Container item
            item_container = QTableWidgetItem(fmt.container.upper())
            item_container.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_container.setTextAlignment(Qt.AlignCenter)
            
            # Codec item
            item_codec = QTableWidgetItem(fmt.vcodec if fmt.vcodec != "none" else fmt.acodec)
            item_codec.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_codec.setTextAlignment(Qt.AlignCenter)
            
            # FPS item
            item_fps = QTableWidgetItem(fmt.fps_label)
            item_fps.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_fps.setTextAlignment(Qt.AlignCenter)
            
            # Size item
            item_size = QTableWidgetItem(fmt.formatted_size)
            item_size.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Audio item
            item_audio = QTableWidgetItem(fmt.audio_label)
            item_audio.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_audio.setTextAlignment(Qt.AlignCenter)
            
            self.table.setItem(row, COL_QUALITY, item_quality)
            self.table.setItem(row, COL_TYPE, item_type)
            self.table.setItem(row, COL_CONTAINER, item_container)
            self.table.setItem(row, COL_CODEC, item_codec)
            self.table.setItem(row, COL_FPS, item_fps)
            self.table.setItem(row, COL_SIZE, item_size)
            self.table.setItem(row, COL_AUDIO, item_audio)

            # Radio button
            radio = QRadioButton(self.table)
            radio.setCursor(Qt.PointingHandCursor)
            self._button_group.addButton(radio, row)
            
            # Center radio in cell
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(radio)
            self.table.setCellWidget(row, COL_SELECT, cell_widget)
            
            radio.clicked.connect(lambda checked=False, r=row: self._on_row_clicked(r, 0))

        # Re-select previously selected format if in view
        if self._selected_format and self._selected_format in self._displayed_formats:
            idx = self._displayed_formats.index(self._selected_format)
            self._set_selected_row(idx)
        elif self._displayed_formats:
            self._set_selected_row(0)

    def _on_row_clicked(self, row: int, col: int):
        if 0 <= row < len(self._displayed_formats):
            self._set_selected_row(row)

    def _set_selected_row(self, row: int):
        self.table.selectRow(row)
        radio = self._button_group.button(row)
        if radio:
            radio.setChecked(True)
        if 0 <= row < len(self._displayed_formats):
            self._selected_format = self._displayed_formats[row]
            self.format_selected.emit(self._selected_format)

    def get_selected_format(self) -> Optional[FormatOption]:
        return self._selected_format

    def select_preset(self, preset_key: str) -> bool:
        """Find and select the closest format matching the preset key."""
        if not self._all_formats:
            return False

        target_fmt: Optional[FormatOption] = None

        if preset_key == "best":
            # Best Video + Audio
            va = [f for f in self._all_formats if f.format_type == "video_audio"]
            if va:
                target_fmt = va[0]
        elif preset_key == "4k":
            candidates = [f for f in self._all_formats if f.format_type == "video_audio" and f.height >= 2160]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "1440p":
            candidates = [f for f in self._all_formats if f.format_type == "video_audio" and f.height == 1440]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "1080p":
            candidates = [f for f in self._all_formats if f.format_type == "video_audio" and f.height == 1080]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "720p":
            candidates = [f for f in self._all_formats if f.format_type == "video_audio" and f.height == 720]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "480p":
            candidates = [f for f in self._all_formats if f.format_type == "video_audio" and f.height == 480]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "mp3_320":
            candidates = [f for f in self._all_formats if f.format_type == "audio_only" and f.container == "mp3" and f.audio_bitrate == 320]
            if candidates:
                target_fmt = candidates[0]
        elif preset_key == "m4a":
            candidates = [f for f in self._all_formats if f.format_type == "audio_only" and f.container == "m4a"]
            if candidates:
                target_fmt = candidates[0]

        if not target_fmt:
            # Fallback to first format
            target_fmt = self._all_formats[0]

        # Switch filter if needed to make target visible
        if target_fmt not in self._displayed_formats:
            self.filter_combo.setCurrentText("All Formats")

        if target_fmt in self._displayed_formats:
            idx = self._displayed_formats.index(target_fmt)
            self._set_selected_row(idx)
            return True

        return False