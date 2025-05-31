import os
import time
import argparse
import signal
from datetime import datetime
from PIL import ImageGrab, Image, ImageDraw, ImageFont
import cv2

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

def capture_screenshot(index):
    img = ImageGrab.grab()
    draw = ImageDraw.Draw(img)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # You can load a custom font if desired
    draw.text((10, 10), timestamp, fill="white")

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

def create_video_from_screenshots():
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".webp")])
    if not files:
        print("[-] No screenshots found.")
        return

    first_img = cv2.imread(os.path.join(OUTPUT_DIR, files[0]))
    height, width, _ = first_img.shape

    default_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    out_path = input(f"Enter path to save the video (default: {default_name}): ").strip()

    if not out_path:
        out_path = default_name

    out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), 1, (width, height))

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
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".webp")])
    if not files:
        print("[-] No screenshots found.")
        return

    first_img = cv2.imread(os.path.join(OUTPUT_DIR, files[0]))
    height, width, _ = first_img.shape

    default_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    out_path = input(f"Enter filename to save the report (default: {default_name}): ").strip()
    if not out_path:
        out_path = default_name

    out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), 1, (width, height))

    for fname in files:
        frames = []

        for i, fname in enumerate(files):
            frame = cv2.imread(os.path.join(OUTPUT_DIR, fname))

            # Repeat each screenshot
            repeat = FRAMES_PER_SHOT

            # If it's the last screenshot and there are multiple screenshots
            if i == len(files) - 1 and len(files) > 1:
                repeat = FINAL_FRAME_HOLD

            frames.extend([frame] * repeat)

        # If only one screenshot, force longer duration
        # if len(files) == 1:
        #     frames.extend([frames[0]] * (MIN_FRAMES_IF_SINGLE - 1))  # already added one

        # Ensure total minimum duration
        while len(frames) < MIN_TOTAL_FRAMES:
            frames.append(frames[-1])

        out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (width, height))
        for frame in frames:
            out.write(frame)
        out.release()
        print(f"[✓] Report saved to: {out_path}")

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