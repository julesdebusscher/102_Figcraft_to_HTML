"""Find, configure and start FigCraft."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_NAME = "config.json"
MAC_EXE = "/Applications/FigCraft.app/Contents/MacOS/FigCraft"


def package_dir():
    return Path(__file__).resolve().parent.parent


def load_config(directory=None):
    path = Path(directory or package_dir()) / CONFIG_NAME
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(directory, cfg):
    path = Path(directory) / CONFIG_NAME
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def candidates(env, platform):
    out = []
    if platform.startswith("win"):
        for var, tail in (
            ("LOCALAPPDATA", ("Programs", "FigCraft", "FigCraft.exe")),
            ("ProgramFiles", ("FigCraft", "FigCraft.exe")),
            ("ProgramFiles(x86)", ("FigCraft", "FigCraft.exe")),
        ):
            base = env.get(var)
            if base:
                out.append(Path(base).joinpath(*tail))
    elif platform == "darwin":
        out.append(Path(MAC_EXE))
    return out


def find_figcraft(config, env=os.environ, platform=sys.platform):
    for p in candidates(env, platform):
        if p.is_file():
            return p
    configured = (config or {}).get("figcraft_path")
    if configured and Path(configured).is_file():
        return Path(configured)
    return None


def launch(path, port, file=None):
    args = [str(path), "--control", str(port)]
    if file:
        args.append(str(file))
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def app_version(path):
    """Ask the executable for its version ('FigCraft 0.18.1 (hash)'); None if unknown."""
    try:
        out = subprocess.run(
            [str(path), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"\d+\.\d+(?:\.\d+)?(?:-[\w.]+)?", out)
    return m.group(0) if m else None
