from dataclasses import dataclass, field
from typing import List, Optional
from app.utils.formatting import format_bytes, format_duration, format_views

@dataclass
class FormatOption:
    """Represents a download format option with all UI-displayable metadata."""
    format_id: str
    format_type: str                  # "video_audio", "video_only", "audio_only", "preset"
    resolution: str                   # "2160p (4K)", "1080p (Full HD)", "Audio 320 kbps"
    height: int = 0
    width: int = 0
    container: str = "mp4"            # "mp4", "webm", "mkv", "mp3", "m4a", "wav"
    vcodec: str = "none"              # "H.264", "VP9", "AV1", "none"
    acodec: str = "none"              # "AAC", "Opus", "MP3", "none"
    fps: Optional[int] = None
    filesize: Optional[int] = None    # In bytes
    audio_bitrate: Optional[int] = None # In kbps
    video_bitrate: Optional[int] = None # In kbps
    dynamic_range: str = "SDR"        # "SDR", "HDR"
    note: str = ""
    is_custom_conversion: bool = False # e.g. extract audio to mp3
    custom_postprocessor_ext: Optional[str] = None
    
    @property
    def formatted_size(self) -> str:
        if self.filesize and self.filesize > 0:
            return format_bytes(self.filesize)
        return "Unknown size"
        
    @property
    def fps_label(self) -> str:
        if self.fps and self.fps > 0:
            return f"{self.fps} FPS"
        return "--"
        
    @property
    def audio_label(self) -> str:
        if self.format_type == "video_only" or self.acodec == "none":
            return "No Audio"
        elif self.format_type == "audio_only":
            bitrate_str = f"{self.audio_bitrate} kbps" if self.audio_bitrate else ""
            return f"{self.acodec} {bitrate_str}".strip()
        else:
            return f"Yes ({self.acodec})" if self.acodec != "none" else "Yes"

    @property
    def type_badge(self) -> str:
        if self.format_type == "video_audio":
            return "Video + Audio"
        elif self.format_type == "video_only":
            return "Video Only"
        elif self.format_type == "audio_only":
            return "Audio Only"
        return "Preset"

@dataclass
class VideoInfo:
    """Represents complete YouTube video metadata and parsed formats."""
    id: str
    url: str
    title: str
    channel: str
    channel_url: str = ""
    duration: int = 0
    thumbnail_url: str = ""
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    description: str = ""
    formats: List[FormatOption] = field(default_factory=list)
    
    @property
    def duration_formatted(self) -> str:
        return format_duration(self.duration)
        
    @property
    def views_formatted(self) -> str:
        return format_views(self.view_count)