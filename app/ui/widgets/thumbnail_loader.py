import urllib.request
from typing import Optional, Dict
from PySide6.QtCore import QThread, Signal, Qt, QRectF
from PySide6.QtGui import QPixmap, QImage, QPainter, QPainterPath, QColor, QFont
from PySide6.QtWidgets import QWidget
from app.services.logger import get_logger

logger = get_logger("ThumbnailLoader")

_THUMBNAIL_CACHE: Dict[str, QPixmap] = {}

class ThumbnailFetchThread(QThread):
    loaded = Signal(QPixmap)
    failed = Signal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        if not self.url:
            self.failed.emit()
            return
            
        if self.url in _THUMBNAIL_CACHE:
            self.loaded.emit(_THUMBNAIL_CACHE[self.url])
            return
            
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                image = QImage.fromData(data)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    _THUMBNAIL_CACHE[self.url] = pixmap
                    self.loaded.emit(pixmap)
                    return
        except Exception as e:
            logger.debug("Failed to fetch thumbnail from %s: %s", self.url, str(e))
            
        self.failed.emit()

class ThumbnailWidget(QWidget):
    """Widget displaying a rounded 16:9 thumbnail with clean minimalist duration badge overlay."""
    def __init__(self, width: int = 220, height: int = 124, parent=None):
        super().__init__(parent)
        self.thumb_width = width
        self.thumb_height = height
        self.setFixedSize(width, height)
        self._pixmap: Optional[QPixmap] = None
        self._duration_text: str = ""
        self._fetch_thread: Optional[ThumbnailFetchThread] = None

    def set_duration(self, duration_text: str):
        self._duration_text = duration_text
        self.update()

    def load_from_url(self, url: str, duration_text: str = ""):
        self._duration_text = duration_text
        self._pixmap = None
        self.update()
        
        if not url:
            return
            
        if url in _THUMBNAIL_CACHE:
            self._pixmap = _THUMBNAIL_CACHE[url]
            self.update()
            return

        if self._fetch_thread and self._fetch_thread.isRunning():
            self._fetch_thread.terminate()
            
        self._fetch_thread = ThumbnailFetchThread(url, self)
        self._fetch_thread.loaded.connect(self._on_loaded)
        self._fetch_thread.failed.connect(self._on_failed)
        self._fetch_thread.start()

    def _on_loaded(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def _on_failed(self):
        self._pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = QRectF(0, 0, self.width(), self.height())
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, 6, 6)
        painter.setClipPath(clip_path)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            # Center crop
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            # Minimal clean placeholder
            painter.fillRect(rect, QColor("#11141B"))
            painter.setPen(QColor("#475569"))
            font = painter.font()
            font.setPointSize(10)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "Video Preview")

        # Subtle dark border
        painter.setPen(QColor("#20242E"))
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 6, 6)

        # Draw duration badge at bottom-right
        if self._duration_text:
            badge_font = QFont("Segoe UI", 9, QFont.Bold)
            painter.setFont(badge_font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(self._duration_text)
            text_h = fm.height()
            
            badge_w = text_w + 10
            badge_h = text_h + 3
            badge_x = self.width() - badge_w - 6
            badge_y = self.height() - badge_h - 6
            
            badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
            badge_path = QPainterPath()
            badge_path.addRoundedRect(badge_rect, 3, 3)
            
            painter.fillPath(badge_path, QColor(15, 17, 21, 210))
            painter.setPen(QColor("#F1F5F9"))
            painter.drawText(badge_rect, Qt.AlignCenter, self._duration_text)