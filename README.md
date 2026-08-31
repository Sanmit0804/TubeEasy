<div align="center">

# 🎬 TubeEasy

**A modern, lightweight, and clutter-free YouTube video & audio downloader for Windows.**

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20(64--bit)-0078D6?style=flat-square&logo=windows)](https://github.com/)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52?style=flat-square&logo=qt)](https://www.qt.io/)
[![Engine](https://img.shields.io/badge/engine-yt--dlp-FF0000?style=flat-square&logo=youtube)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/media-bundled%20FFmpeg-007808?style=flat-square&logo=ffmpeg)](https://ffmpeg.org/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

*TubeEasy packages high-speed format extraction, dynamic audio/video stream merging, audio extraction, and playlist batch downloads into a single standalone `.exe` with zero setup required.*

[Key Features](#-key-features) • [Download & Usage](#-download--usage) • [Building from Source](#-building-the-standalone-exe) • [Architecture](#-architecture) • [Legal Notice](#-legal--terms-of-service)

</div>

---

## ✨ Key Features

- 🚀 **Zero Dependencies (Standalone `.exe`)**: No Python, Node.js, or FFmpeg installation needed. Just double-click `TubeEasy.exe` and start downloading.
- 🎨 **Minimalist Modern Design**: Clean Nordic / Windows 11 Fluent aesthetic with seamless Dark and Light themes. No neon clutter or distracting visuals.
- 🔍 **Deep Format Inspection**: Automatically analyzes YouTube URLs to fetch high-resolution thumbnails, durations, channel info, view counts, and every available video and audio stream.
- ⚙️ **Automatic Stream Merging**: Uses bundled static FFmpeg to merge adaptive video (1080p, 1440p, 4K, 8K) and audio streams into standard MP4 / MKV containers without quality loss.
- 🎵 **Lossless & High-Bitrate Audio**: One-click audio extraction to MP3 (320 kbps & 192 kbps), Apple M4A (AAC), Lossless WAV, and FLAC.
- ⚡ **Quick Quality Presets**: Instant selection buttons for `Best Quality`, `4K UHD`, `1440p 2K`, `1080p FHD`, `720p HD`, `480p SD`, `MP3 (320k)`, and `M4A`.
- 📋 **Smart Playlist Detection**: Detects YouTube playlist links and lets you choose between downloading a single video or batch downloading selected playlist tracks with unified progress tracking.
- 📊 **Real-Time Download Dashboard**: Live progress bar, downloaded / total size, download speed, remaining time (ETA), and current status updates (downloading, merging, converting).
- 📂 **Post-Download Actions**: Quick "Open File" and "Open Folder" buttons upon completion.
- 🛡️ **Windows-Safe Filenames**: Automatically cleans invalid characters (`<>:"/\|?*`), trims long titles, and avoids reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`).
- 🔒 **100% Private & Local**: All downloads and conversions happen entirely on your machine. Zero tracking, telemetry, or third-party servers.

---

## 📥 Download & Usage

### 1. Standalone Executable (Recommended)
1. Download `TubeEasy.exe` from the [Releases](dist/TubeEasy.exe) folder.
2. Place it in any folder and run it.
3. Paste a YouTube URL, click **Analyze**, choose your preferred quality, and click **Download**.

### 2. Supported URL Formats
- Standard watch URLs: `https://www.youtube.com/watch?v=...`
- Short URLs: `https://youtu.be/...`
- YouTube Shorts: `https://www.youtube.com/shorts/...`
- YouTube Playlists: `https://www.youtube.com/playlist?list=...`
- Live streams & mobile links (`m.youtube.com`)

---

## 🏗️ Architecture & Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **GUI Framework** | `PySide6 (Qt 6.11)` | Native, responsive desktop interface with hardware-accelerated rendering |
| **Media Engine** | `yt-dlp` | Fast, robust video metadata extraction and adaptive stream downloading |
| **Audio/Video Processing** | `FFmpeg & FFprobe (Bundled)` | Static Windows binaries for merging video+audio and converting audio codecs |
| **Packaging** | `PyInstaller` | Bundles Qt runtime, Python interpreter, and FFmpeg into a single standalone `.exe` |
| **Configuration** | `JSON / %APPDATA%\TubeEasy` | Persistent user settings (theme, download directory, collision policy) |
| **Logging** | `RotatingFileHandler` | Detailed technical logs stored locally in `%APPDATA%\TubeEasy\logs\app.log` |

```text
TubeEasy/
├── app/
│   ├── main.py                     # Application entry point & exception hooks
│   ├── config/
│   │   └── settings.py             # Persistent settings manager
│   ├── downloader/
│   │   ├── ffmpeg_manager.py       # Detects and manages bundled FFmpeg
│   │   ├── ytdlp_manager.py        # yt-dlp metadata extraction & format parsing
│   │   └── download_worker.py      # QThread background worker with progress hooks
│   ├── models/
│   │   ├── video_info.py           # Video metadata & format data classes
│   │   └── playlist_info.py        # Playlist metadata & item data classes
│   ├── services/
│   │   └── logger.py               # Rotating file logging
│   ├── ui/
│   │   ├── main_window.py          # Main application window
│   │   ├── settings_dialog.py      # Preferences modal
│   │   ├── playlist_dialog.py      # Playlist selection & batch download modal
│   │   ├── styles/
│   │   │   ├── dark.qss            # Minimalist Dark Theme
│   │   │   └── light.qss           # Minimalist Light Theme
│   │   └── widgets/
│   │       ├── format_table.py     # Interactive format selection table
│   │       ├── preset_bar.py       # Quick format preset selector
│   │       ├── progress_card.py    # Live progress bar & post-download actions
│   │       └── thumbnail_loader.py # Async thumbnail loader & duration badge
│   └── utils/
│       ├── formatting.py           # Byte size, duration, speed & view formatters
│       ├── path_utils.py           # Windows filename sanitization & path resolution
│       └── url_validator.py        # YouTube URL matching & playlist detection
├── assets/
│   ├── app_icon.ico                # Multi-resolution application icon
│   └── app_icon.png
├── ffmpeg/
│   ├── ffmpeg.exe                  # Bundled static binary
│   └── ffprobe.exe                 # Bundled static binary
├── tests/                          # Unit test suite (pytest)
├── build.py                        # Automated build & packaging script
├── TubeEasy.spec                   # PyInstaller single-file spec
├── requirements.txt
└── README.md
```

---

## 🛠️ Building the Standalone `.exe`

### 1. Requirements
- **Windows 10 / 11 (64-bit)**
- **Python 3.10+** (Python 3.12 recommended)

### 2. Clone and Install Dependencies
```powershell
git clone https://github.com/your-username/TubeEasy.git
cd TubeEasy
pip install -r requirements.txt
```

### 3. Run Build Script
```powershell
python build.py
```

The automated build script will:
1. Validate all Python dependencies.
2. Verify / download static `ffmpeg.exe` and `ffprobe.exe` binaries into `ffmpeg/`.
3. Run the automated unit test suite with `pytest`.
4. Compile the single-file executable using PyInstaller.
5. Perform an automated smoke test to verify clean launch.

The final executable will be output to:
```text
dist/TubeEasy.exe
```

---

## 🧪 Running Unit Tests

To run the automated test suite:
```powershell
pytest tests/ -v
```

---

## ⚖️ Legal & Terms of Service

> [!IMPORTANT]
> **TubeEasy** is intended for personal use and downloading content that you own, have created, or have express authorization or license to download. Please respect YouTube's Terms of Service and all applicable copyright laws in your jurisdiction.