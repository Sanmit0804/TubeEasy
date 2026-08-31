import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# Ensure UTF-8 output encoding if possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

def log(msg: str):
    print(f"\n[BUILD] >>> {msg}")

def check_dependencies():
    log("Checking Python dependencies...")
    required = ["PySide6", "yt_dlp", "PyInstaller", "PIL", "pytest"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg} available")
        except ImportError:
            print(f"  [FAIL] {pkg} missing! Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(BASE_DIR / "requirements.txt")], check=True)
            break

def check_ffmpeg():
    log("Checking FFmpeg binaries...")
    ffmpeg_exe = BASE_DIR / "ffmpeg" / "ffmpeg.exe"
    ffprobe_exe = BASE_DIR / "ffmpeg" / "ffprobe.exe"
    
    if ffmpeg_exe.is_file() and ffprobe_exe.is_file():
        print(f"  [OK] Found bundled FFmpeg at {ffmpeg_exe}")
        print(f"  [OK] Found bundled FFprobe at {ffprobe_exe}")
        return
        
    print("  [INFO] FFmpeg binaries missing in ffmpeg/ directory! Downloading static Windows build...")
    import urllib.request
    import zipfile
    
    os.makedirs(BASE_DIR / "ffmpeg", exist_ok=True)
    url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = BASE_DIR / "ffmpeg_temp.zip"
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out_f:
        shutil.copyfileobj(resp, out_f)
        
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.endswith("ffmpeg.exe") or name.endswith("ffprobe.exe"):
                fname = os.path.basename(name)
                with z.open(name) as src, open(BASE_DIR / "ffmpeg" / fname, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                    
    if zip_path.exists():
        zip_path.unlink()
    print("  [OK] FFmpeg downloaded and ready.")

def run_tests():
    log("Running automated test suite with pytest...")
    res = subprocess.run([sys.executable, "-m", "pytest", str(BASE_DIR / "tests"), "-v"], cwd=str(BASE_DIR))
    if res.returncode != 0:
        print("  [FAIL] Test suite failed! Aborting build.")
        sys.exit(1)
    print("  [OK] All unit tests passed successfully!")

def build_executable():
    log("Packaging standalone Windows executable with PyInstaller for TubeEasy...")
    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"
    
    # Run PyInstaller with TubeEasy.spec
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(BASE_DIR / "TubeEasy.spec")
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
    
    target_exe = dist_dir / "TubeEasy.exe"
    if not target_exe.exists():
        print("  [FAIL] Build failed: Target executable not found in dist/")
        sys.exit(1)
        
    size_mb = target_exe.stat().st_size / (1024 * 1024)
    log("Build SUCCESSFUL! Executable generated:")
    print(f"  Location: {target_exe}")
    print(f"  File Size: {size_mb:.2f} MB")
    return target_exe

def smoke_test(exe_path: Path):
    log("Performing smoke test on generated TubeEasy executable...")
    print(f"  Testing startup of: {exe_path}")
    
    # Start executable as background process for 4 seconds to verify clean launch without crash
    proc = subprocess.Popen([str(exe_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(4)
    
    poll = proc.poll()
    if poll is not None and poll != 0:
        _, stderr = proc.communicate()
        print(f"  [FAIL] Smoke test failed with returncode {poll}!\nError: {stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)
    else:
        # Process launched cleanly without crashing
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("  [OK] Smoke test passed: TubeEasy launches cleanly without runtime errors or crashes.")

def main():
    print("=" * 65)
    print("  TubeEasy -- Windows Standalone .exe Build System")
    print("=" * 65)
    
    check_dependencies()
    check_ffmpeg()
    run_tests()
    exe = build_executable()
    smoke_test(exe)
    
    print("\n" + "=" * 65)
    print("  All build and packaging steps completed successfully!")
    print(f"  Final deliverable: {exe}")
    print("=" * 65)

if __name__ == "__main__":
    main()