from pathlib import Path
import json, os, subprocess, time, ctypes, psutil, platform


def _config_dir() -> Path:
    if platform.system() == "Windows":
        return (
            Path(os.getenv("APPDATA", Path.home()))
            / "TrackmaniaBatchShadowCalculations"
        )
    if platform.system() == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "trackmania_batch_shadow_calculations"
        )
    base = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(base) / "trackmania_batch_shadow_calculations"


CONFIG_DIR = _config_dir()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"
MAPS_FOLDER_NAME = "Maps"


def running_inside_maps_folder() -> Path:
    cwd = Path.cwd().resolve()
    if cwd.name != MAPS_FOLDER_NAME:
        raise ValueError(f"Run the program from a folder named '{MAPS_FOLDER_NAME}'")
    return cwd


def load_saved_tm_path() -> Path | None:
    if CONFIG_FILE.exists():
        try:
            p = Path(json.loads(CONFIG_FILE.read_text())["tm_path"])
            return p if p.exists() else None
        except Exception:
            return None
    return None


def save_tm_path(path: Path) -> None:
    CONFIG_FILE.write_text(json.dumps({"tm_path": str(path)}))


def brute_force_search() -> list[Path]:
    results = []
    DRIVE_FIXED = 3
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in (chr(65 + i) for i in range(26)):
        if not mask & 1 << (ord(letter) - 65):
            continue
        drive = Path(f"{letter}:\\")
        if ctypes.windll.kernel32.GetDriveTypeW(str(drive)) != DRIVE_FIXED:
            continue
        for root, _, files in os.walk(drive, topdown=True):
            if "Trackmania.exe" in files:
                results.append(Path(root) / "Trackmania.exe")
    return results


def kill_running_tm():
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "Trackmania.exe":
            p.kill()
            p.wait(5)


def normalize_subfolder(text: str) -> str:
    p = Path(text.strip("\"'"))
    lower = [s.lower() for s in p.parts]
    if "maps" in lower:
        idx = lower.index("maps")
        return str(Path(*p.parts[idx + 1 :]))
    return text


def _prepare_and_run(exe: Path, folder: str, quality: str) -> None:
    if any(p.info["name"] == "Trackmania.exe" for p in psutil.process_iter(["name"])):

        raise RuntimeError("Trackmania is running – please close it first.")

    start_compute_shadows(exe, folder, quality)


def start_compute_shadows(
    exe: Path,
    folder: str,
    quality: str = "High",
) -> None:
    rel_folder = normalize_subfolder(folder)
    kill_running_tm()
    proc = subprocess.Popen(
        [
            str(exe),
            f"/computeallshadows={rel_folder}",
            "/fullcheck",
            "/useronly",
            f"/LmQuality={quality}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    last_pid = proc.pid
    while True:
        proc.wait()
        time.sleep(0.5)
        next_procs = [
            p
            for p in psutil.process_iter(["pid", "name"])
            if p.info["name"] == "Trackmania.exe" and p.pid != proc.pid
        ]
        if not next_procs:
            break
        proc = psutil.Process(next_procs[0].pid)
