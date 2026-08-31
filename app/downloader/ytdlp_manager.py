import os
import re
from typing import Dict, Any, List, Optional, Tuple
import yt_dlp
from app.models.video_info import VideoInfo, FormatOption
from app.models.playlist_info import PlaylistInfo, PlaylistItem
from app.downloader.ffmpeg_manager import FFmpegManager
from app.services.logger import get_logger

logger = get_logger("YtDlpManager")

class YtDlpException(Exception):
    """Custom user-friendly exception wrapper for yt-dlp errors."""
    pass

class YtDlpManager:
    @staticmethod
    def get_base_ydl_opts() -> Dict[str, Any]:
        """Generate base yt-dlp configuration options."""
        ffmpeg_path = FFmpegManager.get_ffmpeg_path()
        opts = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "no_color": True,
            "logtostderr": False,
            "encoding": "utf-8",
        }
        if ffmpeg_path:
            # yt-dlp expects the directory containing ffmpeg or the binary path
            opts["ffmpeg_location"] = ffmpeg_path
        return opts

    @classmethod
    def extract_video_info(cls, url: str) -> VideoInfo:
        """Fetch and parse detailed metadata and available download formats for a video."""
        opts = cls.get_base_ydl_opts()
        opts.update({
            "extract_flat": False,
            "skip_download": True,
        })
        
        try:
            logger.info("Extracting video metadata for URL: %s", url)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if not info:
                raise YtDlpException("Failed to retrieve information for this video.")
                
            # If the URL was a playlist and returned entries, pick the first video or main info
            if "entries" in info and info["entries"]:
                info = list(info["entries"])[0]
                
            return cls._build_video_info(info, url)
            
        except yt_dlp.utils.DownloadError as e:
            cls._handle_download_error(str(e))
        except Exception as e:
            logger.error("Unexpected error during info extraction: %s", str(e), exc_info=True)
            raise YtDlpException(f"Unable to analyze video: {str(e)}")

    @classmethod
    def extract_playlist_info(cls, url: str) -> PlaylistInfo:
        """Fetch playlist metadata and item list."""
        opts = cls.get_base_ydl_opts()
        opts.update({
            "extract_flat": "in_playlist",
            "skip_download": True,
        })
        
        try:
            logger.info("Extracting playlist metadata for URL: %s", url)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if not info:
                raise YtDlpException("Failed to retrieve playlist information.")
                
            entries = info.get("entries", [])
            items: List[PlaylistItem] = []
            
            for idx, entry in enumerate(entries, start=1):
                if not entry:
                    continue
                v_id = entry.get("id", "")
                v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                v_title = entry.get("title", f"Video {idx}")
                v_duration = entry.get("duration", 0) or 0
                
                # Get best thumbnail
                v_thumb = ""
                thumbnails = entry.get("thumbnails", [])
                if thumbnails:
                    v_thumb = thumbnails[-1].get("url", "")
                elif entry.get("thumbnail"):
                    v_thumb = entry.get("thumbnail")
                    
                items.append(PlaylistItem(
                    index=idx,
                    id=v_id,
                    url=v_url,
                    title=v_title,
                    duration=v_duration,
                    thumbnail_url=v_thumb,
                    selected=True
                ))
                
            return PlaylistInfo(
                id=info.get("id", ""),
                url=url,
                title=info.get("title", "Untitled Playlist"),
                uploader=info.get("uploader", info.get("channel", "Unknown")),
                item_count=len(items),
                items=items
            )
        except yt_dlp.utils.DownloadError as e:
            cls._handle_download_error(str(e))
        except Exception as e:
            logger.error("Error extracting playlist info: %s", str(e), exc_info=True)
            raise YtDlpException(f"Unable to analyze playlist: {str(e)}")

    @classmethod
    def _build_video_info(cls, info: Dict[str, Any], url: str) -> VideoInfo:
        """Construct a structured VideoInfo instance from raw yt-dlp dictionary."""
        video_id = info.get("id", "")
        title = info.get("title", "Unknown Title")
        channel = info.get("uploader", info.get("channel", "Unknown Channel"))
        channel_url = info.get("channel_url", info.get("uploader_url", ""))
        duration = info.get("duration", 0) or 0
        view_count = info.get("view_count")
        upload_date = info.get("upload_date")
        description = info.get("description", "")
        
        # Get highest resolution thumbnail
        thumbnails = info.get("thumbnails", [])
        thumbnail_url = ""
        if thumbnails:
            # Sort thumbnails by resolution if available
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda t: (t.get("preference", 0) or 0, t.get("width", 0) or 0, t.get("height", 0) or 0),
                reverse=True
            )
            thumbnail_url = sorted_thumbs[0].get("url", "")
        if not thumbnail_url:
            thumbnail_url = info.get("thumbnail", "")

        raw_formats = info.get("formats", [])
        formats = cls._parse_formats(raw_formats, duration)
        
        return VideoInfo(
            id=video_id,
            url=url,
            title=title,
            channel=channel,
            channel_url=channel_url,
            duration=duration,
            thumbnail_url=thumbnail_url,
            view_count=view_count,
            upload_date=upload_date,
            description=description,
            formats=formats
        )

    @classmethod
    def _parse_formats(cls, raw_formats: List[Dict[str, Any]], duration: int) -> List[FormatOption]:
        """
        Analyze and categorize raw yt-dlp streams into clean user options:
        1. Combined Video + Audio streams (auto-merging highest quality audio with video stream)
        2. Audio-only streams (native + common conversions: MP3 320k, MP3 192k, M4A, WAV, FLAC)
        3. Video-only streams
        """
        parsed_options: List[FormatOption] = []
        
        video_streams: List[Dict[str, Any]] = []
        audio_streams: List[Dict[str, Any]] = []
        
        for f in raw_formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            
            has_video = vcodec != "none" and vcodec is not None
            has_audio = acodec != "none" and acodec is not None
            
            # Filter out storyboards / mhtml
            if f.get("format_note") == "storyboard" or f.get("ext") in ("mhtml",):
                continue
                
            if has_video:
                video_streams.append(f)
            elif has_audio:
                audio_streams.append(f)

        # Find best audio stream for pairing
        best_audio = None
        if audio_streams:
            # Sort by abr or tbr
            audio_streams.sort(
                key=lambda a: (a.get("abr") or a.get("tbr") or 0, a.get("filesize") or 0),
                reverse=True
            )
            best_audio = audio_streams[0]

        best_audio_size = (
            best_audio.get("filesize") 
            or best_audio.get("filesize_approx") 
            or (int((best_audio.get("tbr") or best_audio.get("abr") or 128) * 1000 / 8 * duration) if duration else 0)
        ) if best_audio else 0

        # --- 1. Process Video Streams (Merged with Best Audio) ---
        # Group by resolution height and codec to avoid redundant identical rows
        seen_res_codec = set()
        
        # Sort video streams by height descending, then fps, then tbr
        video_streams.sort(
            key=lambda v: (
                v.get("height") or 0,
                v.get("fps") or 0,
                v.get("tbr") or v.get("vbr") or 0
            ),
            reverse=True
        )

        for v in video_streams:
            height = v.get("height") or 0
            if height == 0:
                continue
                
            fps = v.get("fps")
            vcodec = cls._friendly_codec_name(v.get("vcodec", "none"))
            ext = v.get("ext", "mp4")
            if ext not in ("mp4", "webm", "mkv"):
                ext = "mp4"
                
            dyn_range = v.get("dynamic_range", "SDR")
            has_direct_audio = v.get("acodec", "none") not in ("none", None)
            
            key = (height, fps, vcodec, ext)
            if key in seen_res_codec:
                continue
            seen_res_codec.add(key)
            
            # Format ID configuration
            if has_direct_audio:
                fmt_id = v.get("format_id", "")
                acodec_name = cls._friendly_codec_name(v.get("acodec", "none"))
                raw_size = v.get("filesize") or v.get("filesize_approx")
                if not raw_size and duration and (v.get("tbr") or v.get("vbr")):
                    bitrate = v.get("tbr") or v.get("vbr") or 0
                    raw_size = int(bitrate * 1000 / 8 * duration)
            else:
                # Merge with best audio
                if best_audio:
                    fmt_id = f"{v.get('format_id')}+{best_audio.get('format_id')}"
                    acodec_name = cls._friendly_codec_name(best_audio.get("acodec", "none"))
                    v_size = (
                        v.get("filesize") 
                        or v.get("filesize_approx") 
                        or (int((v.get("tbr") or v.get("vbr") or 1500) * 1000 / 8 * duration) if duration else 0)
                    )
                    raw_size = (v_size + best_audio_size) if (v_size and best_audio_size) else None
                else:
                    fmt_id = v.get("format_id", "")
                    acodec_name = "None"
                    raw_size = v.get("filesize") or v.get("filesize_approx")

            res_label = cls._get_resolution_label(height)
            
            parsed_options.append(FormatOption(
                format_id=fmt_id,
                format_type="video_audio",
                resolution=res_label,
                height=height,
                width=v.get("width") or 0,
                container="mp4" if ext == "mp4" else ext,
                vcodec=vcodec,
                acodec=acodec_name,
                fps=fps,
                filesize=raw_size,
                video_bitrate=int(v.get("vbr") or v.get("tbr") or 0),
                dynamic_range=dyn_range,
                note=f"{height}p{fps if fps and fps > 30 else ''} {vcodec}"
            ))

        # --- 2. Process Audio-Only Streams ---
        # A) High Quality Conversions (MP3 320k, MP3 192k, WAV, FLAC, M4A)
        parsed_options.append(FormatOption(
            format_id="bestaudio/best",
            format_type="audio_only",
            resolution="Audio (MP3 High Quality 320 kbps)",
            container="mp3",
            vcodec="none",
            acodec="MP3",
            audio_bitrate=320,
            filesize=int(320 * 1000 / 8 * duration) if duration else None,
            is_custom_conversion=True,
            custom_postprocessor_ext="mp3",
            note="Highest MP3 Bitrate"
        ))
        
        parsed_options.append(FormatOption(
            format_id="bestaudio/best",
            format_type="audio_only",
            resolution="Audio (MP3 Standard 192 kbps)",
            container="mp3",
            vcodec="none",
            acodec="MP3",
            audio_bitrate=192,
            filesize=int(192 * 1000 / 8 * duration) if duration else None,
            is_custom_conversion=True,
            custom_postprocessor_ext="mp3",
            note="Standard MP3"
        ))

        parsed_options.append(FormatOption(
            format_id="bestaudio/best",
            format_type="audio_only",
            resolution="Audio (M4A / AAC Best)",
            container="m4a",
            vcodec="none",
            acodec="AAC",
            audio_bitrate=256,
            filesize=best_audio_size if best_audio_size else (int(256 * 1000 / 8 * duration) if duration else None),
            is_custom_conversion=True,
            custom_postprocessor_ext="m4a",
            note="Apple M4A / AAC"
        ))

        parsed_options.append(FormatOption(
            format_id="bestaudio/best",
            format_type="audio_only",
            resolution="Audio (Lossless WAV)",
            container="wav",
            vcodec="none",
            acodec="PCM",
            audio_bitrate=1411,
            filesize=int(1411 * 1000 / 8 * duration) if duration else None,
            is_custom_conversion=True,
            custom_postprocessor_ext="wav",
            note="Uncompressed Audio"
        ))

        # B) Native audio streams
        seen_audio = set()
        for a in audio_streams:
            acodec = cls._friendly_codec_name(a.get("acodec", "none"))
            abr = int(a.get("abr") or a.get("tbr") or 0)
            ext = a.get("ext", "m4a")
            key = (acodec, abr, ext)
            if key in seen_audio or abr == 0:
                continue
            seen_audio.add(key)
            
            raw_size = a.get("filesize") or a.get("filesize_approx")
            if not raw_size and duration and abr:
                raw_size = int(abr * 1000 / 8 * duration)
                
            parsed_options.append(FormatOption(
                format_id=a.get("format_id", "bestaudio"),
                format_type="audio_only",
                resolution=f"Audio ({acodec} {abr} kbps)",
                container=ext,
                vcodec="none",
                acodec=acodec,
                audio_bitrate=abr,
                filesize=raw_size,
                note=f"Native {ext.upper()}"
            ))

        # --- 3. Standalone Video-Only Streams ---
        for v in video_streams:
            if v.get("acodec", "none") in ("none", None):
                height = v.get("height") or 0
                if height == 0:
                    continue
                vcodec = cls._friendly_codec_name(v.get("vcodec", "none"))
                fps = v.get("fps")
                ext = v.get("ext", "mp4")
                v_size = v.get("filesize") or v.get("filesize_approx")
                if not v_size and duration and (v.get("tbr") or v.get("vbr")):
                    bitrate = v.get("tbr") or v.get("vbr") or 0
                    v_size = int(bitrate * 1000 / 8 * duration)
                    
                parsed_options.append(FormatOption(
                    format_id=v.get("format_id", ""),
                    format_type="video_only",
                    resolution=f"{cls._get_resolution_label(height)} (Muted)",
                    height=height,
                    width=v.get("width") or 0,
                    container=ext,
                    vcodec=vcodec,
                    acodec="none",
                    fps=fps,
                    filesize=v_size,
                    video_bitrate=int(v.get("vbr") or v.get("tbr") or 0),
                    note="No audio stream"
                ))

        return parsed_options

    @staticmethod
    def _friendly_codec_name(raw_codec: str) -> str:
        """Convert technical codec identifiers to human-readable strings."""
        if not raw_codec or raw_codec == "none":
            return "none"
        raw_lower = raw_codec.lower()
        if "avc1" in raw_lower or "h264" in raw_lower:
            return "H.264"
        elif "vp9" in raw_lower:
            return "VP9"
        elif "av01" in raw_lower or "av1" in raw_lower:
            return "AV1"
        elif "hevc" in raw_lower or "h265" in raw_lower or "hev1" in raw_lower:
            return "H.265"
        elif "mp4a" in raw_lower or "aac" in raw_lower:
            return "AAC"
        elif "opus" in raw_lower:
            return "Opus"
        elif "mp3" in raw_lower:
            return "MP3"
        elif "vorbis" in raw_lower:
            return "Vorbis"
        elif "flac" in raw_lower:
            return "FLAC"
        return raw_codec.split(".")[0]

    @staticmethod
    def _get_resolution_label(height: int) -> str:
        """Produce standard label like 2160p (4K UHD), 1080p (Full HD), etc."""
        if height >= 4320:
            return "4320p (8K UHD)"
        elif height >= 2160:
            return "2160p (4K UHD)"
        elif height >= 1440:
            return "1440p (2K QHD)"
        elif height >= 1080:
            return "1080p (Full HD)"
        elif height >= 720:
            return "720p (HD)"
        elif height >= 480:
            return "480p (SD)"
        elif height >= 360:
            return "360p"
        elif height >= 240:
            return "240p"
        elif height >= 144:
            return "144p"
        return f"{height}p"

    @classmethod
    def _handle_download_error(cls, msg: str):
        """Map raw yt-dlp errors to friendly user messages."""
        logger.warning("yt-dlp error: %s", msg)
        msg_lower = msg.lower()
        if "private video" in msg_lower:
            raise YtDlpException("This video is private. You do not have permission to access it.")
        elif "video unavailable" in msg_lower or "deleted" in msg_lower:
            raise YtDlpException("This video has been removed or is no longer available on YouTube.")
        elif "sign in to confirm your age" in msg_lower or "age-restricted" in msg_lower:
            raise YtDlpException("This video is age-restricted and requires user authentication.")
        elif "members-only content" in msg_lower or "join this channel" in msg_lower:
            raise YtDlpException("This video is restricted to channel members.")
        elif "not available in your country" in msg_lower or "geo-restricted" in msg_lower:
            raise YtDlpException("This video is blocked in your geographical region.")
        elif "unable to download webpage" in msg_lower or "connection refused" in msg_lower or "timed out" in msg_lower:
            raise YtDlpException("Network connection failed. Please check your internet connection and try again.")
        elif "copyright" in msg_lower:
            raise YtDlpException("This video is unavailable due to a copyright claim.")
        else:
            # Clean up raw error string
            clean_msg = re.sub(r'ERROR:\s*(\[[^\]]+\])?\s*', '', msg).strip()
            raise YtDlpException(clean_msg or "Unable to process video URL. Please verify the URL and try again.")