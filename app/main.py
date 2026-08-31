import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont
from app.services.logger import setup_logger, get_logger
from app.downloader.ffmpeg_manager import FFmpegManager
from app.ui.main_window import MainWindow

logger = get_logger("Main")

def global_exception_hook(exctype, value, tb):
    """Global exception handler to capture unhandled exceptions and log them."""
    import traceback
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical("Unhandled Exception caught:\n%s", err_msg)
    
    # If a QApplication exists, show a friendly message box
    if QApplication.instance():
        QMessageBox.critical(
            None,
            "Unexpected Application Error",
            f"An unexpected error occurred in TubeEasy:\n\n{str(value)}\n\n"
            "The error details have been recorded in the application log file."
        )
    sys.__excepthook__(exctype, value, tb)

def main():
    # Setup logger and global crash handler
    setup_logger()
    sys.excepthook = global_exception_hook
    logger.info("Starting TubeEasy...")

    # Configure Qt High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TubeEasy")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TubeEasy")

    # Set default modern font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Initialize FFmpeg discovery
    FFmpegManager.initialize()

    # Create and display Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()