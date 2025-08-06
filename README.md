# Screenshot Logger

Screen logger reports your screen activity. The best companion for Pomodoro technique to track not only your time but all screen activity for reports!

A simple Python tool that periodically captures your screen, saves screenshots with timestamps, and compiles them into a video as proof of work.

![video](https://github.com/user-attachments/assets/da4ef1ad-6c45-4271-8a98-4eed272a4311)

## 📦 Install with `uv`

```bash
uv venv
uv pip install -r pyproject.toml
```

## Install

```sh
uv venv
```

## Use

### Start background screenshot collection

```sh
uv run python screenshot_logger.py --collect
```

### Later, compile video from screenshots

```sh
uv run python screenshot_logger.py --report
```

### As cli

```sh
cd path/to/screenshot_logger
uv run python -m screenshot_logger --report
```

### Export zipped images folder option with UTC time

```sh
uv run screenshot_logger.py --utc --img
```
