import pytest
from app.utils.formatting import format_bytes, format_duration, format_speed, format_eta

def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1048576) == "1.00 MB"
    assert format_bytes(1073741824) == "1.00 GB"
    assert format_bytes(None) == "Unknown size"

def test_format_duration():
    assert format_duration(45) == "0:45"
    assert format_duration(125) == "2:05"
    assert format_duration(3665) == "1:01:05"
    assert format_duration(0) == "0:00"
    assert format_duration(None) == "Unknown"

def test_format_speed():
    assert format_speed(1048576) == "1.00 MB/s"
    assert format_speed(0) == "-- MB/s"
    assert format_speed(None) == "-- MB/s"

def test_format_eta():
    assert format_eta(65) == "1:05"
    assert format_eta(None) == "--:--"