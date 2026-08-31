import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from app.utils.path_utils import get_base_dir
from app.services.logger import get_logger

logger = get_logger("FFmpegManager")

class FFmpegManager:
    _ffmpeg_path: Optional[str] = None
    _ffprobe_path: Optional[str] = None
    _version: Optional[str] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> bool:
        """Locate ffmpeg and ffprobe binaries."""
        if cls._initialized and cls._ffmpeg_path:
            return True
            
        cls._ffmpeg_path, cls._ffprobe_path = cls._find_binaries()
        if cls._ffmpeg_path:
            cls._version = cls._query_version(cls._ffmpeg_path)
            logger.info("Found FFmpeg at %s (Version: %s)", cls._ffmpeg_path, cls._version)
        else:
            logger.warning("FFmpeg executable not found in bundle, application directory, or system PATH.")
            
        cls._initialized = True
        return cls._ffmpeg_path is not None

    @classmethod
    def _find_binaries(cls) -> Tuple[Optional[str], Optional[str]]:
        """Search for ffmpeg.exe and ffprobe.exe in priority order."""
        ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
        
        candidates = []
        
        # 1. Check PyInstaller _MEIPASS bundle directory
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates.append(meipass / "ffmpeg")
            candidates.append(meipass)
            
        # 2. Check directory next to sys.executable
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "ffmpeg")
        candidates.append(exe_dir)
        
        # 3. Check project base directory
        base_dir = get_base_dir()
        candidates.append(base_dir / "ffmpeg")
        candidates.append(base_dir)
        
        # 4. Check current working directory
        candidates.append(Path.cwd() / "ffmpeg")
        candidates.append(Path.cwd())
        
        found_ffmpeg = None
        found_ffprobe = None
        
        for folder in candidates:
            ffmpeg_file = folder / ffmpeg_name
            ffprobe_file = folder / ffprobe_name
            if ffmpeg_file.is_file() and os.access(ffmpeg_file, os.X_OK | os.R_OK):
                found_ffmpeg = str(ffmpeg_file.resolve())
                if ffprobe_file.is_file():
                    found_ffprobe = str(ffprobe_file.resolve())
                break
                
        # 5. Fallback to system PATH
        if not found_ffmpeg:
            system_ffmpeg = shutil.which(ffmpeg_name)
            if system_ffmpeg:
                found_ffmpeg = system_ffmpeg
                system_ffprobe = shutil.which(ffprobe_name)
                if system_ffprobe:
                    found_ffprobe = system_ffprobe
                    
        return found_ffmpeg, found_ffprobe

    @classmethod
    def _query_version(cls, ffmpeg_path: str) -> str:
        """Run ffmpeg -version and parse the first line."""
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
            res = subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo,
                timeout=5,
                check=True
            )
            first_line = res.stdout.splitlines()[0] if res.stdout else "Unknown version"
            return first_line.strip()
        except Exception as e:
            logger.error("Error querying FFmpeg version: %s", str(e))
            return "FFmpeg (detected)"

    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        if not cls._initialized:
            cls.initialize()
        return cls._ffmpeg_path

    @classmethod
    def get_ffprobe_path(cls) -> Optional[str]:
        if not cls._initialized:
            cls.initialize()
        return cls._ffprobe_path

    @classmethod
    def is_available(cls) -> bool:
        if not cls._initialized:
            cls.initialize()
        return cls._ffmpeg_path is not None

    @classmethod
    def get_version(cls) -> str:
        if not cls._initialized:
            cls.initialize()
        return cls._version or "Not installed / Not found"