from typing import Optional, Union

def format_bytes(bytes_count: Optional[Union[int, float]]) -> str:
    """Format a byte count into a human-readable string (e.g. 15.4 MB, 1.25 GB)."""
    if bytes_count is None or bytes_count < 0:
        return "Unknown size"
    
    if bytes_count == 0:
        return "0 B"
        
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    val = float(bytes_count)
    
    while val >= 1024.0 and unit_index < len(units) - 1:
        val /= 1024.0
        unit_index += 1
        
    if unit_index == 0:
        return f"{int(val)} B"
    elif val >= 100:
        return f"{val:.1f} {units[unit_index]}"
    else:
        return f"{val:.2f} {units[unit_index]}"

def format_duration(seconds: Optional[Union[int, float]]) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS string."""
    if seconds is None or seconds < 0:
        return "Unknown"
        
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def format_speed(bytes_per_sec: Optional[Union[int, float]]) -> str:
    """Format download speed into MB/s or KB/s."""
    if bytes_per_sec is None or bytes_per_sec <= 0:
        return "-- MB/s"
    return f"{format_bytes(bytes_per_sec)}/s"

def format_eta(seconds: Optional[Union[int, float]]) -> str:
    """Format remaining ETA seconds into human-readable string."""
    if seconds is None or seconds < 0:
        return "--:--"
    return format_duration(seconds)

def format_views(view_count: Optional[int]) -> str:
    """Format view count with commas (e.g. 1,234,567 views)."""
    if view_count is None:
        return "Unknown views"
    return f"{view_count:,} views"