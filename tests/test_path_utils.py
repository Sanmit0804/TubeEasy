import pytest
from pathlib import Path
from app.utils.path_utils import sanitize_filename, get_unique_filepath, get_default_download_dir

def test_sanitize_filename_basic():
    assert sanitize_filename("Normal Video Title") == "Normal Video Title"
    assert sanitize_filename("Video / with \\ illegal : chars * ? < > |") == "Video _ with _ illegal _ chars _ _ _ _ _"

def test_sanitize_filename_reserved_names():
    assert sanitize_filename("CON") == "_CON"
    assert sanitize_filename("nul.mp4") == "_nul.mp4"
    assert sanitize_filename("aux.txt") == "_aux.txt"

def test_sanitize_filename_length_trim():
    long_title = "A" * 250 + ".mp4"
    sanitized = sanitize_filename(long_title, max_length=100)
    assert len(sanitized) <= 100
    assert sanitized.endswith(".mp4")

def test_get_unique_filepath(tmp_path):
    f = tmp_path / "video.mp4"
    f.touch()
    
    unique1 = get_unique_filepath(str(f))
    assert unique1 == str(tmp_path / "video (1).mp4")
    
    Path(unique1).touch()
    unique2 = get_unique_filepath(str(f))
    assert unique2 == str(tmp_path / "video (2).mp4")