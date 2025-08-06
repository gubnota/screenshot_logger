import os
import platform
import time
import argparse
import signal
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import mss
import cv2
from collections import defaultdict
from img_export import create_zip_from_screenshots
from vars import CONFIG

RUNNING = True
MERGE_MONITORS = False

def timestamped_filename(index, suffix=""):
    dt = (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if USE_UTC
        else datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    return os.path.join(CONFIG.OUTPUT_DIR, f"{index:04d}{suffix}_{dt}{'Z' if USE_UTC else ''}.webp")

def get_system_font(size=36):
    system = platform.system()
    font_paths = CONFIG.FONT_PATHS
    for path in font_paths.get(system, []):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    print("[!] Warning: Using default small font.")
    return ImageFont.load_default()

def capture_screenshot(index, print_label=True):
    global USE_UTC
    with mss.mss() as sct:
        monitor_count = len(sct.monitors) - 1
        timestamp = (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
            if USE_UTC
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        if monitor_count < 1:
            print(f"[!] {timestamp} No monitors found. Maybe in sleeping mode?")
            return

        if MERGE_MONITORS or monitor_count == 1:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            if print_label:
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
            img.save(path, "WEBP", quality=CONFIG.WEBP_QUALITY)
            print(f"[+] Screenshot saved: {path}")
        else:
            for i, monitor in enumerate(sct.monitors[1:], start=1):
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                if print_label:
                    draw = ImageDraw.Draw(img)
                    timestamp = (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
            if USE_UTC
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
                    font = get_system_font(24)
                    label = f"Monitor {i}: {timestamp}"
                    text_bbox = draw.textbbox((0, 0), label, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    x = (img.width - text_width) / 2
                    draw.text((x, 1), label, fill="white", font=font)
                path = timestamped_filename(index, f"_monitor{i}")
                img.save(path, "WEBP", quality=CONFIG.WEBP_QUALITY)
                print(f"[+] Screenshot (monitor {i}) saved: {path}")

def periodic_loop(print_label=True):
    os.makedirs(CONFIG.OUTPUT_DIR, exist_ok=True)
    count = 0
    while RUNNING:
        capture_screenshot(count, print_label)
        count += 1
        time.sleep(CONFIG.CAPTURE_INTERVAL)

def create_video_from_screenshots():
    files = sorted([f for f in os.listdir(CONFIG.OUTPUT_DIR) if f.endswith(".webp")])
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
            img = cv2.imread(os.path.join(CONFIG.OUTPUT_DIR, fname))
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

        if monitor_id == "merged":
            output_path = f"report_{timestamp}.mp4"
        else:
            output_path = f"report_{timestamp}_m{monitor_id}.mp4"
        out = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), CONFIG.FPS, (max_width, max_height)
        )
        frame_count = 0
        last_frame = None
        for fname in monitor_files:
            frame = cv2.imread(os.path.join(CONFIG.OUTPUT_DIR, fname))
            if frame is None:
                continue
            h, w = frame.shape[:2]
            if w != max_width or h != max_height:
                if UPSCALE:
                    # Scale to max resolution (may stretch if AR doesn't match)
                    frame = cv2.resize(frame, (max_width, max_height), interpolation=cv2.INTER_LINEAR)
                else:
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
    global RUNNING, args, USE_UTC
    print("\n[!] Stopping collection. Finalizing report...")
    RUNNING = False
    time.sleep(1)
    if getattr(args, "img", False):#if args.img:
        create_zip_from_screenshots()
    else:
        create_video_from_screenshots()
    cleanup_screenshots()
    exit(0)


def cleanup_screenshots():
    if not os.path.exists(CONFIG.OUTPUT_DIR):
        print("[*] No screenshots directory to clean.")
        return
    for f in os.listdir(CONFIG.OUTPUT_DIR):
        if f.endswith(".webp"):
            os.remove(os.path.join(CONFIG.OUTPUT_DIR, f))
    print("[*] Temporary screenshots cleaned up.")

if __name__ == "__main__":
    global args, USE_UTC
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
    # Default is upscale=True; --no-upscale or --center will disable upscaling
    parser.add_argument(
        "--no-upscale",
        "--center",
        action="store_false",
        dest="upscale",
        help="Disable upscaling; center/pad smaller frames instead.",
    )
    # do not print datetime/label on screenshots
    parser.add_argument(
    "--no-datetime",
    action="store_true",
    help="Do not print datetime/label on screenshots.",
    )
## output zip file of screenshots and universal time
    parser.add_argument(
        "--img",
        action="store_true",
        help="Export screenshots as ZIP archive (no compression).",
    )
    parser.add_argument(
        "--utc",
        action="store_true",
        help="Use UTC timestamps instead of local time."
    )
    parser.set_defaults(upscale=True)
    args = parser.parse_args()
    MERGE_MONITORS = args.merge
    UPSCALE = args.upscale
    PRINT_LABEL = not args.no_datetime
    USE_UTC = args.utc

    if not args.collect and not args.report:
        args.collect = True

    if args.collect:
        cleanup_screenshots()
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        print(f"[+] Starting screenshot collection (merge mode: {MERGE_MONITORS})...")
        periodic_loop(PRINT_LABEL)
    elif args.report:
        try:
            create_video_from_screenshots()
        except KeyboardInterrupt:
            print("\n[!] Interrupted during save prompt. Cleaning screenshots.")
            cleanup_screenshots()
    elif args.img:
        create_zip_from_screenshots()
        cleanup_screenshots()