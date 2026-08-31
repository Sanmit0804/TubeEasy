import os
import sys
import re
from pathlib import Path

RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

def get_base_dir() -> Path:
    """Return the base directory of the running application or source tree."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    # Root of the repo (parent of app directory)
    return Path(__file__).resolve().parent.parent.parent

def get_resource_path(relative_path: str) -> Path:
    """Resolve the absolute path to a bundled resource asset."""
    base = get_base_dir()
    return base / relative_path

def get_app_data_dir() -> Path:
    """Return the persistent application data directory in %APPDATA%/TubeEasy."""
    app_data = os.environ.get('APPDATA')
    if app_data:
        base = Path(app_data) / 'TubeEasy'
    else:
        base = Path.home() / '.tubeeasy'
    base.mkdir(parents=True, exist_ok=True)
    return base

def get_default_download_dir() -> str:
    """Return a sensible default download directory for TubeEasy downloads."""
    user_profile = os.environ.get('USERPROFILE')
    if user_profile:
        videos_dir = Path(user_profile) / 'Videos' / 'TubeEasy Downloads'
    else:
        videos_dir = Path.home() / 'Videos' / 'TubeEasy Downloads'
    try:
        videos_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return str(videos_dir)

def sanitize_filename(name: str, max_length: int = 180) -> str:
    """
    Sanitize a string to be a safe, valid Windows filename.
    Removes invalid characters, strips leading/trailing spaces/dots,
    prevents Windows reserved device names, and trims long titles.
    """
    if not name:
        return 'download'
    
    # Replace illegal Windows characters: < > : " / \ | ? * and ASCII control characters (0-31)
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    
    # Remove excessive whitespace or underscores
    cleaned = re.sub(r'\s+', ' ', cleaned).strip('. ')
    cleaned = re.sub(r'_+', '_', cleaned)
    
    if not cleaned:
        cleaned = 'download'
        
    # Check for reserved DOS / Windows device names
    base_name = cleaned.split('.')[0].upper()
    if base_name in RESERVED_NAMES:
        cleaned = f'_{cleaned}'
        
    # Truncate length while preserving reasonable extension if present
    if len(cleaned) > max_length:
        parts = cleaned.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) <= 6:
            stem, ext = parts[0], parts[1]
            cleaned = f'{stem[:max_length - len(ext) - 1].rstrip()}.{ext}'
        else:
            cleaned = cleaned[:max_length].rstrip()
            
    return cleaned

def get_unique_filepath(target_path: str) -> str:
    """If the file already exists, append (1), (2), etc. to produce a unique path."""
    path = Path(target_path)
    if not path.exists():
        return target_path
        
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    
    counter = 1
    while True:
        candidate = parent / f'{stem} ({counter}){suffix}'
        if not candidate.exists():
            return str(candidate)
        counter += 1