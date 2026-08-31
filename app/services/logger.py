import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.utils.path_utils import get_app_data_dir

_LOGGER_INITIALIZED = False

def setup_logger() -> logging.Logger:
    """Initialize TubeEasy application root logger with rotating file and console handlers."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger("TubeEasy")
    
    if _LOGGER_INITIALIZED:
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # Create log directory
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    
    # File handler (max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    _LOGGER_INITIALIZED = True
    logger.info("TubeEasy logger initialized. Log file: %s", str(log_file))
    return logger

def get_logger(name: str = "TubeEasy") -> logging.Logger:
    """Get a named logger instance."""
    setup_logger()
    return logging.getLogger(f"TubeEasy.{name}")

def get_log_file_path() -> Path:
    """Return the absolute path to the log file."""
    return get_app_data_dir() / "logs" / "app.log"