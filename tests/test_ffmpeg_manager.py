import pytest
from app.downloader.ffmpeg_manager import FFmpegManager

def test_ffmpeg_detection():
    is_avail = FFmpegManager.is_available()
    assert is_avail is True, "FFmpeg should be detected in local ffmpeg/ folder"
    
    path = FFmpegManager.get_ffmpeg_path()
    assert path is not None
    assert "ffmpeg.exe" in path.lower()
    
    version = FFmpegManager.get_version()
    assert "ffmpeg version" in version.lower()