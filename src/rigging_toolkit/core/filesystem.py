from pathlib import Path
from typing import Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

latest_regex = r"(?P<name>.*)\.v(?P<version>\d\d\d)\.(?P<extension>.*)"

file_regex = r"(?P<name>.*)\.(?P<extension>.*)"

DEBUG = False

def create_path(path):
    # type: (Path) -> Path
    if not path.exists():
        path.mkdir(parents=True)

def validate_path(path, create_missing=False):
    # type: (Path, Optional[bool]) -> Path
    if not path.exists():
        if create_missing is True:
            create_path(path)
            return path
        raise ValueError(f"Cannot Validate Path: {path} does not exist.")
    return path

def has_folders(path):
    # type: (Path) -> bool
    path = validate_path(path)

    folders = list(path.iterdir())

    if not folders:
        return False
    return True

def find_latest(folder, versioned_name, extension):
    # type: (Path, str, str) -> Tuple[Optional[Path], int]
    latest = None
    latest_version = -1

    folder = validate_path(folder)

    if extension:
        if not extension.startswith("."):
            extension = f".{extension}"

    for file in folder.iterdir():
        if not file.is_file():
            continue

        match = re.search(latest_regex, file.name)

        if not match:
            continue

        name = match.group("name")
        version = int(match.group("version"))
        ext = match.group("extension")
        if ext:
            ext = f".{ext}"

        name_matches = name == versioned_name
        extension_matches = extension == ext
        is_latest = latest_version < version

        if name_matches and extension_matches and is_latest:
            latest = file
            latest_version = version

    if latest:
        latest = latest.resolve()

    return (latest, latest_version)

def find_latest_partial(folder, partial_name, extension):
    # type: (Path, str, str) -> Tuple[Optional[Path], int]
    """Finds the latest file that contains the partial_name and extension."""
    latest = None
    latest_version = -1

    folder = validate_path(folder)

    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue

        match = re.search(latest_regex, file_path.name)

        if not match:
            if DEBUG:
                print(
                    f"find_latest_partial: Match Not Found -- file_path.name: {file_path.name}"
                )
            continue

        if DEBUG:
            print(f"find_latest_partial: Found Match")
        name = match.group("name")
        version = int(match.group("version"))
        ext = match.group("extension")

        name_contains = partial_name in name
        if DEBUG:
            print(
                f"find_latest_partial: name_contains {name_contains} -- name {name} -- partial {partial_name}"
            )
        extension_matches = extension == ext
        is_latest = latest_version < version

        if name_contains and is_latest and extension_matches:
            latest = file_path
            latest_version = version
    if DEBUG:
        print(f"find_latest_partial: latest -> {file_path} latest_version -> {version}")
    return (latest, latest_version)

def find_file(folder, file_name, extension):
    # type: (Path, str, str) -> Optional[Path]
    
    folder = validate_path(folder)
    latest = None

    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue

        match = re.search(file_regex, file_path.name)

        if not match:
            if DEBUG:
                print(f"find_file: Match Not Found -- file_path.name: {file_path.name}")
            continue

        if DEBUG:
            print(f"find_file: Found Match")
        
        name = match.group("name")
        ext = match.group("extension")

        name_matches = file_name == name
        extension_matches = extension == ext

        if name_matches and extension_matches:
            latest = file_path

    if latest:
        latest = latest.resolve()

    return latest

def find_new_version(folder, versioned_name, extension):
    # type: (Path, str, str) -> Tuple[Optional[Path], int]
    folder = validate_path(folder)

    latest, latest_version = find_latest(folder=folder, versioned_name=versioned_name, extension=extension)

    if not latest:
        latest = folder.resolve(strict=False) / "dummy_file"
        latest_version = 0

    new_version = latest_version + 1
    new_path = latest.parent / f"{versioned_name}.v{new_version:03d}.{extension}"

    return (new_path, new_version)