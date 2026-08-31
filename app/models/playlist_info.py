from dataclasses import dataclass, field
from typing import List
from app.utils.formatting import format_duration

@dataclass
class PlaylistItem:
    """Represents a single video entry inside a playlist."""
    index: int
    id: str
    url: str
    title: str
    duration: int = 0
    thumbnail_url: str = ""
    selected: bool = True
    status: str = "Pending"          # "Pending", "Downloading", "Completed", "Failed", "Cancelled"
    progress: float = 0.0            # 0.0 to 100.0
    error_message: str = ""
    
    @property
    def duration_formatted(self) -> str:
        return format_duration(self.duration)

@dataclass
class PlaylistInfo:
    """Represents playlist metadata and its collection of video items."""
    id: str
    url: str
    title: str
    uploader: str = "Unknown"
    item_count: int = 0
    items: List[PlaylistItem] = field(default_factory=list)