import pytest
from app.utils.url_validator import is_valid_youtube_url, is_playlist_url, extract_video_id, clean_youtube_url

def test_valid_youtube_urls():
    assert is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("http://youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("https://www.youtube.com/shorts/abcdefghijk") is True
    assert is_valid_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("https://www.youtube.com/playlist?list=PL123456789") is True

def test_invalid_youtube_urls():
    assert is_valid_youtube_url("") is False
    assert is_valid_youtube_url("https://vimeo.com/123456") is False
    assert is_valid_youtube_url("https://google.com") is False
    assert is_valid_youtube_url("not a url") is False
    assert is_valid_youtube_url("https://youtube.com") is False
    assert is_valid_youtube_url("https://youtube.com/watch") is False

def test_playlist_detection():
    assert is_playlist_url("https://www.youtube.com/playlist?list=PL123456789") is True
    assert is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123456789") is True
    assert is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is False
    assert is_playlist_url("https://youtu.be/dQw4w9WgXcQ") is False

def test_extract_video_id():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_clean_youtube_url():
    dirty = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&si=12345&t=30"
    cleaned = clean_youtube_url(dirty)
    assert "v=dQw4w9WgXcQ" in cleaned
    assert "t=30" in cleaned
    assert "feature=share" not in cleaned
    assert "si=12345" not in cleaned