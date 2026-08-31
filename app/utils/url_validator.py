import re
from urllib.parse import urlparse, parse_qs, urlunparse

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "gaming.youtube.com",
    "youtu.be",
}

# Regex to match youtube URL forms
YOUTUBE_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?.*v=|shorts/|embed/|playlist\?|live/)|youtu\.be/)[a-zA-Z0-9_-]+',
    re.IGNORECASE
)

def is_valid_youtube_url(url: str) -> bool:
    """Check if the provided string is a valid YouTube URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain not in YOUTUBE_DOMAINS and not any(domain.endswith("." + d) for d in ["youtube.com", "youtu.be"]):
            return False
            
        # Check standard watch URL
        if "youtube.com" in domain:
            if parsed.path.startswith("/watch"):
                query = parse_qs(parsed.query)
                return "v" in query and len(query["v"][0]) > 0
            elif parsed.path.startswith(("/shorts/", "/embed/", "/v/", "/live/", "/playlist")):
                return len(parsed.path.strip("/").split("/")) >= 2 or parsed.path.startswith("/playlist")
        elif "youtu.be" in domain:
            return len(parsed.path.strip("/")) > 0
            
        return bool(YOUTUBE_REGEX.match(url))
    except Exception:
        return False

def is_playlist_url(url: str) -> bool:
    """Check if the URL contains a YouTube playlist identifier."""
    if not url or not isinstance(url, str):
        return False
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "list" in query and query["list"][0]:
            # Filter out standard mixes or radio playlists if needed, but 'list' generally indicates a playlist
            return True
        if parsed.path.startswith("/playlist"):
            return "list" in query
        return False
    except Exception:
        return False

def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID if present."""
    if not url:
        return ""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/").split("/")[0].split("?")[0]
        elif "youtube.com" in parsed.netloc:
            if parsed.path.startswith("/watch"):
                query = parse_qs(parsed.query)
                return query.get("v", [""])[0]
            elif parsed.path.startswith(("/shorts/", "/embed/", "/v/", "/live/")):
                parts = [p for p in parsed.path.split("/") if p]
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass
    return ""

def clean_youtube_url(url: str) -> str:
    """Normalize the URL by stripping tracking parameters while preserving video ID and playlist ID."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        allowed_params = ["v", "list", "index", "t"]
        filtered_query = {k: v for k, v in query.items() if k in allowed_params}
        
        # Build query string
        pairs = []
        for k in allowed_params:
            if k in filtered_query:
                for val in filtered_query[k]:
                    pairs.append(f"{k}={val}")
        new_query = "&".join(pairs)
        
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            new_query,
            ""
        ))
    except Exception:
        return url