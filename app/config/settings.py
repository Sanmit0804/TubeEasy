import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from app.utils.path_utils import get_app_data_dir, get_default_download_dir
from app.services.logger import get_logger

logger = get_logger("Settings")

@dataclass
class AppSettings:
    # General
    download_dir: str = field(default_factory=get_default_download_dir)
    auto_open_folder: bool = False
    remember_url: bool = False
    last_url: str = ""
    
    # Downloads
    max_simultaneous_downloads: int = 2
    filename_template: str = "%(title)s.%(ext)s"
    overwrite_behavior: str = "rename"  # "rename", "overwrite", "skip"
    
    # Audio Conversion
    preferred_audio_format: str = "mp3"  # "mp3", "m4a", "wav", "flac"
    audio_quality_kbps: int = 320
    
    # Appearance
    theme: str = "dark"  # "dark", "light", "system"
    
    # Advanced
    embed_thumbnail: bool = True
    embed_metadata: bool = True

class SettingsManager:
    _instance: Optional['SettingsManager'] = None
    
    def __init__(self):
        self._settings_path = get_app_data_dir() / "settings.json"
        self._settings = AppSettings()
        self.load()
        
    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance
        
    @property
    def settings(self) -> AppSettings:
        return self._settings
        
    def load(self) -> AppSettings:
        """Load settings from JSON file or create defaults."""
        if not self._settings_path.exists():
            logger.info("Settings file not found, using default configuration.")
            self.save()
            return self._settings
            
        try:
            with open(self._settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Populate settings fields
            valid_fields = AppSettings.__dataclass_fields__.keys()
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            self._settings = AppSettings(**filtered_data)
            
            # Ensure download dir exists
            if not os.path.exists(self._settings.download_dir):
                try:
                    os.makedirs(self._settings.download_dir, exist_ok=True)
                except Exception:
                    self._settings.download_dir = get_default_download_dir()
                    
            logger.info("Settings loaded successfully from %s", self._settings_path)
        except Exception as e:
            logger.error("Failed to load settings file, resetting to defaults: %s", str(e))
            self._settings = AppSettings()
            self.save()
            
        return self._settings
        
    def save(self) -> bool:
        """Save current settings to JSON file."""
        try:
            get_app_data_dir().mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self._settings), f, indent=4)
            logger.info("Settings saved to %s", self._settings_path)
            return True
        except Exception as e:
            logger.error("Failed to save settings: %s", str(e))
            return False
            
    def update(self, **kwargs) -> bool:
        """Update specific settings and save."""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        return self.save()