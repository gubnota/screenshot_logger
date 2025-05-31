import os
import platform
import time
import argparse
import signal
from datetime import datetime
from PIL import ImageGrab, Image, ImageDraw, ImageFont
import cv2
import shutil
import subprocess

# CONFIG
CAPTURE_INTERVAL = 60  # seconds
OUTPUT_DIR = "screenshots"
WEBP_QUALITY = 85
RUNNING = True
FPS = 1  # frames per second
FRAMES_PER_SHOT = 1  # number of frames to repeat per screenshot (i.e. 2 seconds duration)
MIN_TOTAL_FRAMES = 3  # force at least 3 frames in video
MIN_FRAMES_IF_SINGLE = 3
FINAL_FRAME_HOLD = 3  # how long to hold the last screenshot (in frames)

def timestamped_filename(index):
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{index:04d}_{dt}.webp")

def get_system_font(size=36):
    system = platform.system()

    font_paths = {
        "Darwin": [  # macOS
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Monaco.ttf",
        ],
        "Windows": [  # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Calibri.ttf",
        ],
        "Linux": [  # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    }

    for path in font_paths.get(system, []):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    print("[!] Warning: Using default small font.")
    return ImageFont.load_default()

def capture_screenshot(index):
    img = ImageGrab.grab()
    draw = ImageDraw.Draw(img)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    font = get_system_font(24)

    img_width, _ = img.size
    text_bbox = draw.textbbox((0, 0), timestamp, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    x = (img_width - text_width) / 2
    y = 1

    draw.text((x, y), timestamp, fill="white", font=font)

    path = timestamped_filename(index)
    img.save(path, "WEBP", quality=WEBP_QUALITY)
    print(f"[+] Screenshot saved: {path}")

def periodic_loop():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count = 0
    while RUNNING:
        capture_screenshot(count)
        count += 1
        time.sleep(CAPTURE_INTERVAL)

def create_video_from_screenshots(out_path=None):
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".webp")])
    if not files:
        print("[-] No screenshots found.")
        return

    default_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    if not out_path:
        out_path = input(f"Enter path to save the video (default: {default_name}): ").strip()
        if not out_path:
            out_path = default_name

    # Check if ffmpeg is available
    if shutil.which("ffmpeg"):
        print("[*] Using ffmpeg to generate video...")
        cmd = [
            "ffmpeg",
            "-framerate", str(FPS),
            "-pattern_type", "glob",
            "-i", os.path.join(OUTPUT_DIR, "*.webp"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-y", out_path
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"[✓] Video saved to: {out_path}")
        except subprocess.CalledProcessError as e:
            print("[-] ffmpeg failed:", e)
    else:
        print("[*] ffmpeg not found. Falling back to OpenCV...")
        first_img = cv2.imread(os.path.join(OUTPUT_DIR, files[0]))
        height, width, _ = first_img.shape
        out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (width, height))
        for fname in files:
            frame = cv2.imread(os.path.join(OUTPUT_DIR, fname))
            out.write(frame)
        out.release()
        print(f"[✓] Video saved to: {out_path}")

def handle_exit(signum, frame):
    global RUNNING
    print("\n[!] Stopping collection. Finalizing report...")

    RUNNING = False
    time.sleep(1)  # Give last screenshot time to finish

    create_video_on_exit()
    cleanup_screenshots()
    exit(0)
def create_video_on_exit():
    default_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    try:
        out_path = input(f"Enter filename to save the report (default: {default_name}): ").strip()
    except KeyboardInterrupt:
        print("\n[!] Interrupted during filename prompt. Skipping report generation.")
        return

    if not out_path:
        out_path = default_name

    create_video_from_screenshots(out_path=out_path)

def cleanup_screenshots():
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".webp"):
            os.remove(os.path.join(OUTPUT_DIR, f))
    print("[*] Temporary screenshots cleaned up.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Screenshot logger")
    parser.add_argument("--collect", action="store_true", help="Start collecting screenshots periodically")
    parser.add_argument("--report", action="store_true", help="Create a report video from collected screenshots")
    args = parser.parse_args()

    if args.collect:
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        print("[+] Starting screenshot collection...")
        periodic_loop()

    elif args.report:
        print("[+] Creating report video...")
        create_video_from_screenshots()

    else:
        print("Usage:")
        print("  python screenshot_logger.py --collect     # Start background capture")
        print("  python screenshot_logger.py --report      # Compile video report")

def handle_exit_clean_only(signum, frame):
    global RUNNING
    print("\n[!] Stopping collection. Cleaning up screenshots.")
    RUNNING = False
    time.sleep(1)
    cleanup_screenshots()
    exit(0)
def main():
    parser = argparse.ArgumentParser(description="Screenshot logger")
    parser.add_argument("--collect", action="store_true", help="Start collecting screenshots periodically")
    parser.add_argument("--report", action="store_true", help="Create a report video from collected screenshots")
    args = parser.parse_args()

    # Default to --collect if no args
    if not args.collect and not args.report:
        args.collect = True

    if args.collect:
        cleanup_screenshots()  # ✅ clean previous session on start
        signal.signal(signal.SIGINT, handle_exit_clean_only)
        signal.signal(signal.SIGTERM, handle_exit_clean_only)
        print("[+] Starting screenshot collection...")
        periodic_loop()

    elif args.report:
        try:
            create_video_from_screenshots()
        except KeyboardInterrupt:
            print("\n[!] Interrupted during save prompt. Cleaning screenshots.")
            cleanup_screenshots()