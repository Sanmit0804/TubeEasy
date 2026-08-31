import pytest
from app.downloader.ytdlp_manager import YtDlpManager

def test_format_parser():
    mock_raw_formats = [
        {
            "format_id": "137",
            "vcodec": "avc1.640028",
            "acodec": "none",
            "height": 1080,
            "width": 1920,
            "fps": 30,
            "tbr": 3500,
            "filesize": 50000000,
            "ext": "mp4"
        },
        {
            "format_id": "140",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "abr": 128,
            "filesize": 5000000,
            "ext": "m4a"
        },
        {
            "format_id": "22",
            "vcodec": "avc1.64001F",
            "acodec": "mp4a.40.2",
            "height": 720,
            "width": 1280,
            "fps": 30,
            "filesize": 25000000,
            "ext": "mp4"
        }
    ]
    
    options = YtDlpManager._parse_formats(mock_raw_formats, duration=120)
    assert len(options) > 0
    
    # Check that merged 1080p exists
    f1080 = [f for f in options if f.height == 1080 and f.format_type == "video_audio"]
    assert len(f1080) > 0
    assert "137+140" in f1080[0].format_id
    assert f1080[0].vcodec == "H.264"
    assert f1080[0].acodec == "AAC"
    
    # Check that MP3 audio conversions exist
    mp3s = [f for f in options if f.container == "mp3"]
    assert len(mp3s) >= 2