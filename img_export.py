from datetime import datetime
import os
import zipfile
from vars import CONFIG

def create_zip_from_screenshots():
    files = sorted([f for f in os.listdir(CONFIG.OUTPUT_DIR) if f.endswith(".webp")])
    if not files:
        print("[-] No screenshots found.")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"screenshots_{timestamp}.zip"
    zip_path = os.path.join(".", zip_filename)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for fname in files:
            full_path = os.path.join(CONFIG.OUTPUT_DIR, fname)
            zf.write(full_path, arcname=fname)
    print(f"[✓] ZIP archive saved to: {zip_path}")
