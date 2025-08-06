from types import SimpleNamespace

CONFIG = SimpleNamespace(
    # General settings
    OUTPUT_DIR="screenshots",
    CAPTURE_INTERVAL=60,  # seconds
    WEBP_QUALITY=85,
    FPS=1,

    # Font paths
    FONT_PATHS={
        "Darwin": [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Monaco.ttf",
        ],
        "Windows": [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Calibri.ttf",
        ],
        "Linux": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ],
    }
)