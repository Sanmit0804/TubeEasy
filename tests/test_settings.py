import pytest
import json
from app.config.settings import SettingsManager, AppSettings

def test_settings_save_and_load(tmp_path, monkeypatch):
    test_json = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.settings.get_app_data_dir", lambda: tmp_path)
    
    mgr = SettingsManager()
    mgr._settings_path = test_json
    
    mgr.update(theme="light", auto_open_folder=True, max_simultaneous_downloads=4)
    
    assert test_json.exists()
    
    # New instance loading same file
    mgr2 = SettingsManager()
    mgr2._settings_path = test_json
    loaded = mgr2.load()
    
    assert loaded.theme == "light"
    assert loaded.auto_open_folder is True
    assert loaded.max_simultaneous_downloads == 4