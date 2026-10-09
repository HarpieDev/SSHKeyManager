import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(debug: bool = False) -> None:
    base = (Path(os.environ["HARPIE_HOME"]) / "AppData" / "Local") if os.environ.get("HARPIE_HOME") else Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    log_dir = base / "HarpieSSH" / "logs"

    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        root.addHandler(logging.NullHandler())

    if debug:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        root.addHandler(console)
