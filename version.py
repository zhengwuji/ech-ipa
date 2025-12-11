import json
import os
from typing import Tuple


VERSION_FILE = "version.json"
VERSION_MIN = (1, 0, 0)
VERSION_MAX = (9, 9, 99)


def _read_version() -> Tuple[int, int, int]:
    if not os.path.exists(VERSION_FILE):
        return VERSION_MIN
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    major, minor, patch = data.get("major", 1), data.get("minor", 0), data.get("patch", 0)
    return int(major), int(minor), int(patch)


def _write_version(v: Tuple[int, int, int]) -> str:
    major, minor, patch = v
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"major": major, "minor": minor, "patch": patch}, f, ensure_ascii=False, indent=2)
    return f"{major}.{minor}.{patch:02d}"


def current_version() -> str:
    v = _read_version()
    return f"{v[0]}.{v[1]}.{v[2]:02d}"


def bump_version() -> str:
    major, minor, patch = _read_version()
    patch += 1
    if patch > VERSION_MAX[2]:
        patch = 0
        minor += 1
    if minor > VERSION_MAX[1]:
        minor = 0
        major += 1
    if major > VERSION_MAX[0]:
        major, minor, patch = VERSION_MIN
    return _write_version((major, minor, patch))

