import os
import sys
import re
from typing import Optional, Dict, Any
from pathlib import Path
from PySide6.QtCore import QThread, Signal
import yt_dlp
from app.models.video_info import FormatOption, VideoInfo
from app.downloader.ffmpeg_manager import FFmpegManager
from app.utils.path_utils import sanitize_filename, get_unique_filepath
from app.config.settings import SettingsManager
from app.services.logger import get_logger

logger = get_logger("DownloadWorker")

class DownloadWorker(QThread):
    """
    Background worker thread executing yt-dlp media downloads, stream merges,
    and audio conversions while reporting real-time progress to the UI.
    """
    progress_signal = Signal(dict)       # {percentage, downloaded_bytes, total_bytes, speed, eta, status}
    status_signal = Signal(str)          # status message string
    finished_signal = Signal(str)        # final downloaded file path
    error_signal = Signal(str)           # error message string
    cancelled_signal = Signal()          # cancellation notification

    def __init__(
        self,
        video_info: VideoInfo,
        format_option: FormatOption,
        output_dir: str,
        custom_filename: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.video_info = video_info
        self.format_option = format_option
        self.output_dir = output_dir
        self.custom_filename = custom_filename
        self._is_cancelled = False
        self._final_filepath: Optional[str] = None
        self._ydl: Optional[yt_dlp.YoutubeDL] = None

    def cancel(self):
        """Signal the worker to cancel the active download."""
        logger.info("Cancellation requested for video: %s", self.video_info.title)
        self._is_cancelled = True

    def run(self):
        try:
            self._is_cancelled = False
            self.status_signal.emit("Preparing download...")
            logger.info("Starting download for: %s | Format: %s", self.video_info.title, self.format_option.format_id)

            settings = SettingsManager.get_instance().settings
            
            # Ensure target directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Base sanitized filename
            safe_title = sanitize_filename(self.custom_filename or self.video_info.title)
            out_tmpl = os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
            
            ffmpeg_path = FFmpegManager.get_ffmpeg_path()
            
            ydl_opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "no_color": True,
                "outtmpl": out_tmpl,
                "progress_hooks": [self._progress_hook],
                "postprocessor_hooks": [self._postprocessor_hook],
                "encoding": "utf-8",
                "windowsfilenames": True,
            }
            
            if ffmpeg_path:
                ydl_opts["ffmpeg_location"] = ffmpeg_path
                
            # Embedding metadata / thumbnail if available
            if settings.embed_metadata and ffmpeg_path:
                ydl_opts["addmetadata"] = True

            # Configure format & post-processing based on FormatOption
            if self.format_option.is_custom_conversion:
                # Audio conversion (MP3, WAV, M4A)
                ydl_opts["format"] = self.format_option.format_id
                target_ext = self.format_option.custom_postprocessor_ext or "mp3"
                
                postprocessors = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": target_ext,
                }]
                if target_ext == "mp3" and self.format_option.audio_bitrate:
                    postprocessors[0]["preferredquality"] = str(self.format_option.audio_bitrate)
                    
                ydl_opts["postprocessors"] = postprocessors
                
            elif self.format_option.format_type == "video_audio":
                # Merge video + audio
                ydl_opts["format"] = self.format_option.format_id
                ydl_opts["merge_output_format"] = self.format_option.container or "mp4"
                
            elif self.format_option.format_type == "video_only":
                ydl_opts["format"] = self.format_option.format_id
                
            elif self.format_option.format_type == "audio_only":
                ydl_opts["format"] = self.format_option.format_id
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._ydl = ydl
                
                if self._is_cancelled:
                    self._cleanup_partial()
                    self.cancelled_signal.emit()
                    return
                    
                info_dict = ydl.extract_info(self.video_info.url, download=True)
                
                if self._is_cancelled:
                    self._cleanup_partial()
                    self.cancelled_signal.emit()
                    return
                    
                # Determine the final downloaded filepath
                if not self._final_filepath:
                    if info_dict:
                        filename = ydl.prepare_filename(info_dict)
                        # Check if audio was converted
                        if self.format_option.is_custom_conversion:
                            target_ext = self.format_option.custom_postprocessor_ext or "mp3"
                            stem = Path(filename).stem
                            filename = str(Path(filename).parent / f"{stem}.{target_ext}")
                        elif self.format_option.format_type == "video_audio":
                            target_ext = self.format_option.container or "mp4"
                            stem = Path(filename).stem
                            filename = str(Path(filename).parent / f"{stem}.{target_ext}")
                            
                        self._final_filepath = filename

            if self._is_cancelled:
                self._cleanup_partial()
                self.cancelled_signal.emit()
                return

            if self._final_filepath and os.path.exists(self._final_filepath):
                logger.info("Download completed successfully: %s", self._final_filepath)
                self.progress_signal.emit({
                    "percentage": 100.0,
                    "downloaded_bytes": os.path.getsize(self._final_filepath),
                    "total_bytes": os.path.getsize(self._final_filepath),
                    "speed": 0,
                    "eta": 0,
                    "status": "Download completed"
                })
                self.status_signal.emit("Download completed")
                self.finished_signal.emit(self._final_filepath)
            else:
                # Check directory for matching safe_title
                matched_file = self._find_downloaded_file(safe_title)
                if matched_file:
                    self._final_filepath = matched_file
                    logger.info("Matched downloaded file: %s", self._final_filepath)
                    self.finished_signal.emit(self._final_filepath)
                else:
                    self.error_signal.emit("Download finished but target file could not be located.")

        except yt_dlp.utils.DownloadCancelled:
            logger.info("Download cancelled exception caught.")
            self._cleanup_partial()
            self.cancelled_signal.emit()
        except Exception as e:
            if self._is_cancelled:
                self._cleanup_partial()
                self.cancelled_signal.emit()
                return
            logger.error("Download failed with exception: %s", str(e), exc_info=True)
            self.error_signal.emit(f"Download failed: {str(e)}")

    def _progress_hook(self, d: Dict[str, Any]):
        """Callback invoked by yt-dlp during stream downloading."""
        if self._is_cancelled:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
            
        status = d.get("status")
        
        if status == "downloading":
            downloaded = d.get("downloaded_bytes", 0) or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            speed = d.get("speed", 0) or 0
            eta = d.get("eta", 0) or 0
            
            percentage = 0.0
            if total > 0:
                percentage = min(100.0, (downloaded / total) * 100.0)
            elif "_percent_str" in d:
                try:
                    pct_str = re.sub(r'[^\d.]', '', d["_percent_str"])
                    percentage = float(pct_str)
                except Exception:
                    percentage = 0.0
                    
            status_text = "Downloading stream..."
            filename = d.get("filename", "")
            if filename:
                if ".f" in filename: # Adaptive stream indicator
                    status_text = "Downloading video/audio stream..."
                else:
                    status_text = "Downloading media..."

            self.progress_signal.emit({
                "percentage": percentage,
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed": speed,
                "eta": eta,
                "status": status_text
            })
            
        elif status == "finished":
            self.status_signal.emit("Stream download complete. Processing...")
            filename = d.get("filename")
            if filename and not self._final_filepath:
                self._final_filepath = filename

    def _postprocessor_hook(self, d: Dict[str, Any]):
        """Callback invoked during post-processing (FFmpeg merge, audio convert)."""
        if self._is_cancelled:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")
            
        postprocessor = d.get("postprocessor", "")
        status = d.get("status", "")
        
        if status == "started":
            if "Merger" in postprocessor or "FFmpegMerger" in postprocessor:
                msg = "Merging video and audio streams (FFmpeg)..."
            elif "ExtractAudio" in postprocessor or "FFmpegExtractAudio" in postprocessor:
                msg = f"Converting audio to {self.format_option.container.upper()} (FFmpeg)..."
            elif "Fixup" in postprocessor:
                msg = "Fixing container metadata..."
            else:
                msg = f"Post-processing: {postprocessor}..."
                
            self.status_signal.emit(msg)
            self.progress_signal.emit({
                "percentage": 99.0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "speed": 0,
                "eta": 0,
                "status": msg
            })
            
        elif status == "finished":
            info_dict = d.get("info_dict", {})
            filepath = info_dict.get("filepath")
            if filepath:
                self._final_filepath = filepath

    def _find_downloaded_file(self, safe_title: str) -> Optional[str]:
        """Look for any recently created file matching safe_title in the output dir."""
        try:
            out_path = Path(self.output_dir)
            candidates = list(out_path.glob(f"{safe_title}.*"))
            # Exclude temp / part files
            candidates = [c for c in candidates if not c.name.endswith((".part", ".ytdl", ".temp"))]
            if candidates:
                # Sort by modification time
                candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                return str(candidates[0].resolve())
        except Exception:
            pass
        return None

    def _cleanup_partial(self):
        """Remove unfinished .part / .ytdl files on cancellation."""
        try:
            safe_title = sanitize_filename(self.custom_filename or self.video_info.title)
            out_path = Path(self.output_dir)
            for part in out_path.glob(f"{safe_title}*.part"):
                try:
                    part.unlink(missing_ok=True)
                except Exception:
                    pass
            for ytdl in out_path.glob(f"{safe_title}*.ytdl"):
                try:
                    ytdl.unlink(missing_ok=True)
                except Exception:
                    pass
            if self._final_filepath and os.path.exists(self._final_filepath):
                try:
                    os.remove(self._final_filepath)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Error during partial file cleanup: %s", str(e))