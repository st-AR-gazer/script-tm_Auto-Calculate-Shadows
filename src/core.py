from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import time
import ctypes
import psutil
import platform


def _config_dir() -> Path:
    if platform.system() == "Windows":
        root = Path(os.getenv("APPDATA", Path.home()))
        return root / "TrackmaniaShadowCalc"
    if platform.system() == "Darwin":
        return (
            Path.home() / "Library" / "Application Support" / "trackmania_shadow_calc"
        )
    xdg = os.getenv("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config" / "trackmania_shadow_calc"


CONFIG_DIR = _config_dir()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

MAPS_FOLDER_NAME = "Maps"


def running_inside_maps_folder() -> Path:
    cwd = Path.cwd().resolve()
    if cwd.name != MAPS_FOLDER_NAME:
        raise ValueError(
            f"Run the program from a folder named '{MAPS_FOLDER_NAME}', "
            f"not from '{cwd.name}'."
        )
    return cwd


def load_saved_tm_path() -> Path | None:
    if CONFIG_FILE.exists():
        try:
            path = Path(json.loads(CONFIG_FILE.read_text())["tm_path"])
            return path if path.exists() else None
        except Exception:
            return None
    return None


def save_tm_path(path: Path) -> None:
    CONFIG_FILE.write_text(json.dumps({"tm_path": str(path)}))


def brute_force_search() -> list[Path]:
    results: list[Path] = []
    DRIVE_FIXED = 3
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in (chr(65 + i) for i in range(26)):
        if not bitmask & 1 << (ord(letter) - 65):
            continue
        drive = Path(f"{letter}:\\")
        if ctypes.windll.kernel32.GetDriveTypeW(str(drive)) != DRIVE_FIXED:
            continue
        for root, _, files in os.walk(drive, topdown=True):
            if "Trackmania.exe" in files:
                results.append(Path(root) / "Trackmania.exe")
    return results


def kill_running_tm():
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] == "Trackmania.exe":
            proc.kill()
            proc.wait(5)


def normalize_subfolder(user_input: str) -> str:
    p = Path(user_input.strip("\"'"))
    parts = [part.lower() for part in p.parts]

    if "maps" in parts:
        idx = parts.index("maps")
        rel_parts = p.parts[idx + 1 :]
        return str(Path(*rel_parts))
    return user_input


def start_compute_shadows(
    tm_path: Path,
    map_subfolder: str,
    quality: str = "High",
) -> None:
    rel_folder = normalize_subfolder(map_subfolder)
    kill_running_tm()

    cmd = [
        str(tm_path),
        f"/computeallshadows={rel_folder}",
        "/fullcheck",
        "/useronly",
        f"/LmQuality={quality}",
    ]
    subprocess.Popen(cmd)

    while any(p.name() == "Trackmania.exe" for p in psutil.process_iter()):
        time.sleep(1)
