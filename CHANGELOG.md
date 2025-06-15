# v0.0.2

Multiple screens support

## Standard capture (one image per monitor if multiple)

python screenshot_logger_multi_monitor.py --collect

## Merge all monitors into a single screenshot

python screenshot_logger_multi_monitor.py --collect --merge

# v0.0.3

```sh
sleep 2; uv run python3 screenshot_logger.py
```

- [x] If resolution changes in time it will center smaller images
- [x] for shorter videos one or two extra frames will be added
- [x] long name was replaced with shorter ones (m1, m2 for monitors)
