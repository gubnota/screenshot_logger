import os
import platform
import time
import argparse
import signal
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import mss
import shutil
import subprocess
import cv2
from collections import defaultdict

# CONFIG
CAPTURE_INTERVAL = 60  # seconds
OUTPUT_DIR = "screenshots"
WEBP_QUALITY = 85
RUNNING = True
FPS = 1
MERGE_MONITORS = False


def timestamped_filename(index, suffix=""):
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{index:04d}{suffix}_{dt}.webp")


def get_system_font(size=36):
    system = platform.system()
    font_paths = {
        "Darwin": [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Monaco.ttf",
        ],
        "Windows": ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/Calibri.ttf"],
        "Linux": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ],
    }
    for path in font_paths.get(system, []):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    print("[!] Warning: Using default small font.")
    return ImageFont.load_default()


def capture_screenshot(index):
    # with mss.mss() as sct:
    #     monitor_count = len(sct.monitors) - 1
    with mss.mss() as sct:
        monitor_count = len(sct.monitors) - 1  # sct.monitors[0] — merged
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if monitor_count < 1:
            print(f"[!] {timestamp} No monitors found. Maybe in sleeping mode?")
            return

        if MERGE_MONITORS or monitor_count == 1:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            draw = ImageDraw.Draw(img)
            font = get_system_font(24)
            label = (
                f"{timestamp} (merged)"
                if MERGE_MONITORS and monitor_count > 1
                else timestamp
            )
            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            x = (img.width - text_width) / 2
            draw.text((x, 1), label, fill="white", font=font)
            path = timestamped_filename(index)
            img.save(path, "WEBP", quality=WEBP_QUALITY)
            print(f"[+] Screenshot saved: {path}")
        else:
            for i, monitor in enumerate(sct.monitors[1:], start=1):
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                draw = ImageDraw.Draw(img)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                font = get_system_font(24)
                label = f"Monitor {i}: {timestamp}"
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                x = (img.width - text_width) / 2
                draw.text((x, 1), label, fill="white", font=font)
                path = timestamped_filename(index, f"_monitor{i}")
                img.save(path, "WEBP", quality=WEBP_QUALITY)
                print(f"[+] Screenshot (monitor {i}) saved: {path}")


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

    monitor_frames = defaultdict(list)
    for f in files:
        if "_monitor" in f:
            name_part = f.split("_monitor")[1]
            monitor_id = name_part.split("_")[0]
            monitor_frames[monitor_id].append(f)
        else:
            monitor_frames["merged"].append(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for monitor_id, monitor_files in monitor_frames.items():
        monitor_files.sort()
        # STEP 1: Scan for largest resolution
        max_width, max_height = 0, 0
        for fname in monitor_files:
            img = cv2.imread(os.path.join(OUTPUT_DIR, fname))
            if img is None:
                continue
            h, w = img.shape[:2]
            if w > max_width:
                max_width = w
            if h > max_height:
                max_height = h
        if max_width == 0 or max_height == 0:
            print(f"[-] No valid frames for monitor {monitor_id}")
            continue

        # STEP 2: Create video with max resolution, pad if needed
        if monitor_id == "merged":
            output_path = f"report_{timestamp}.mp4"
        else:
            output_path = f"report_{timestamp}_m{monitor_id}.mp4"
        out = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (max_width, max_height)
        )
        frame_count = 0
        last_frame = None
        for fname in monitor_files:
            frame = cv2.imread(os.path.join(OUTPUT_DIR, fname))
            if frame is None:
                continue
            h, w = frame.shape[:2]
            if w != max_width or h != max_height:
                # Pad image to max resolution (black borders)
                top = (max_height - h) // 2
                bottom = max_height - h - top
                left = (max_width - w) // 2
                right = max_width - w - left
                frame = cv2.copyMakeBorder(
                    frame, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0)
                )
            out.write(frame)
            frame_count += 1
            last_frame = frame

        # Add extra frames at the end
        if last_frame is not None:
            if frame_count == 1:
                out.write(last_frame)
                out.write(last_frame)
            else:
                out.write(last_frame)
        out.release()
        print(f"[✓] Video for monitor {monitor_id} saved to: {output_path}")

def handle_exit(signum, frame):
    global RUNNING
    print("\n[!] Stopping collection. Finalizing report...")
    RUNNING = False
    time.sleep(1)
    create_video_from_screenshots()
    cleanup_screenshots()
    exit(0)


def cleanup_screenshots():
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".webp"):
            os.remove(os.path.join(OUTPUT_DIR, f))
    print("[*] Temporary screenshots cleaned up.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Screenshot logger with per-monitor video export"
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Start collecting screenshots periodically",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Create a report video from collected screenshots",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Capture all monitors as a single merged image",
    )
    args = parser.parse_args()

    MERGE_MONITORS = args.merge

    if not args.collect and not args.report:
        args.collect = True

    if args.collect:
        cleanup_screenshots()
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        print(f"[+] Starting screenshot collection (merge mode: {MERGE_MONITORS})...")
        periodic_loop()
    elif args.report:
        try:
            create_video_from_screenshots()
        except KeyboardInterrupt:
            print("\n[!] Interrupted during save prompt. Cleaning screenshots.")
            cleanup_screenshots()
