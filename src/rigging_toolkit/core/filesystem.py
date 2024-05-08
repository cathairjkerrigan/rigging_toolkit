from pathlib import Path as _Path
from typing import Optional, Tuple, List
import logging
import os
import re
from collections import OrderedDict
from pathlib import _posix_flavour, _windows_flavour
from datetime import datetime
logger = logging.getLogger(__name__)

latest_regex = r"(?P<name>.*)\.v(?P<version>\d\d\d)\.(?P<extension>.*)"
version_regex = re.compile(r"\.v\d{3}")
file_regex = r"(?P<name>.*)\.(?P<extension>.*)"

DEBUG = False

class Path(_Path):

    _flavour = _windows_flavour if os.name == "nt" else _posix_flavour

    _version_data = None  #  type: Optional[Tuple[int, int]]

    _asset_name = None  # type: Optional[str]
    _lod_level = None  # type: Optional[int]
    _unversioned_stem = None  # type: Optional[str]
    _unversioned_name = None  # type: Optional[str]
    _unversioned_suffix = None  # type: Optional[str]

    @staticmethod
    def create_path(path):
        # type: (Path) -> Path
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)

    @staticmethod
    def validate_path(path, create_missing=False, raise_error=False):
        # type: (Path, Optional[bool], Optional[bool]) -> Path
        if path is None:
            return None
        path = Path(path)
        if not path.exists():
            if path is None and raise_error:
                raise ValueError(f"Cannot Validate Path: {path}")
            if path is None:
                if DEBUG: logger.warning(f"Cannot Validate Path: {path}")
                return None
            if create_missing is True:
                Path.create_path(path)
                return path
            if raise_error:
                raise ValueError(f"Cannot Validate Path: {path} does not exist.")
            else:
                if DEBUG: logger.warning(f"Cannot Validate Path: {path} does not exist.")
                return None
        return Path(path)

    @property
    def has_folders(self):
        # type: () -> bool

        folders = [x for x in self.iterdir() if x.is_dir()]

        if not folders:
            return False
        return True

    @property
    def has_files(self):
        # type: () -> bool

        files = [x for x in self.iterdir() if x.is_file()]

        if not files:
            return False
        return True

    @property
    def has_items(self):
        # type: () -> bool

        items = list(self.iterdir())

        if not items:
            return False
        return True

    @staticmethod
    def get_folders(path, ignore_list=None):
        # type: (Path, Optional[List[str]]) -> Optional[List[Path]]
        path = Path(path)
        if not path.has_folders:
            return
        if ignore_list:
            folders = [x for x in path.iterdir() if x.is_dir() and x.name not in ignore_list]
        else:
            folders = [x for x in path.iterdir() if x.is_dir()]
        return folders
    
    @property
    def version(self):
        # type: () -> int
        return self._find_version_data()[0]
    
    @property
    def has_version(self):
        # type: () -> bool
        return self.version > 0
    
    @property
    def is_versioned(self):
        # type: () -> bool
        try:
            self._find_version_data()
            return True
        except ValueError:
            return False
        
    @property
    def creation_date(self):
        # type: () -> str
        return datetime.fromtimestamp(self.stat().st_ctime).strftime("%d/%m/%Y")
    
    @property
    def file_size(self):
        # type: () -> str
        return self._get_file_size_str()
        
    @property
    def unversioned_stem(self):
        # type: () -> str

        if self._unversioned_stem is not None:
            return self._unversioned_stem

        version, index = self._find_version_data()

        if version == 0:
            if "." in self.name:
                # everything before the first '.' is the stem
                if self.name.startswith("."):
                    return "." + self.name.split(".", 2)[1]
                else:
                    return self.name.split(".", 1)[0]
            else:
                # there is no '.' in the name, so the whole name is the stem
                return self.name

        suffixes = self.suffixes
        for i, s in enumerate(self.suffixes):
            if version_regex.match(s):
                suffixes = self.suffixes[i:]
                break

        self._unversioned_stem = self.name[0 : len(self.name) - len("".join(suffixes))]

        return self._unversioned_stem
        
    @property
    def unversioned_name(self):
        # type: () -> str

        if self._unversioned_name is not None:
            return self._unversioned_name

        version, index = self._find_version_data()

        suffixes = self.suffixes
        if version > 0:
            del suffixes[index]
        else:
            index = 0

        self._unversioned_name = self.unversioned_stem + self.unversioned_suffix

        return self._unversioned_name
        
    @property
    def unversioned_suffix(self):
        # type: () -> str

        if self._unversioned_suffix is not None:
            return self._unversioned_suffix

        version, index = self._find_version_data()
        self._unversioned_suffix = "".join(self.suffixes[index + 1 :])

        return self._unversioned_suffix
            
    def _find_version_data(self):
        # type: () -> Tuple[int, int]

        if self._version_data is not None:
            return self._version_data
        
        version = 0
        index = -1
        matches = []

        for idx, suffix in enumerate(reversed(self.suffixes)):
            match = version_regex.match(suffix)
            if match:
                matches.append(match)
                index = len(self.suffixes) - idx - 1

        if len(matches) > 1:
            raise ValueError(f"Multiple version suffixes found: {self}")
        
        if index > 0:
            raise ValueError(f"Version suffix not before all other extensions: {self}")
        
        if matches:
            version = int(matches[0].group(0)[2:])

            if version == 0:
                raise ValueError(f"Version should be >= 1: {self}")
            
        self._version_data = (version, index)
        return self._version_data
    
    def _get_file_size_str(self):
        # type: () -> str
        size_in_bytes = self.stat().st_size

        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']

        # Determine the appropriate size unit
        suffix_index = 0
        while size_in_bytes >= 1024 and suffix_index < len(suffixes) - 1:
            size_in_bytes /= 1024.0
            suffix_index += 1

        return f"{size_in_bytes:.2f} {suffixes[suffix_index]}"


def find_latest(folder, versioned_name, extension):
    # type: (Path, str, str) -> Tuple[Optional[Path], int]
    latest = None
    latest_version = -1

    folder = Path.validate_path(folder)

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

def find_all_latest(folder, extension):
    # type: (Path, Optional[str]) -> List[Path]
    folder = Path.validate_path(folder)
    if not folder:
        return

    all_stems = []

    latest_files = []

    for file in folder.iterdir():
        if not file.is_file():
            continue
        
        all_stems.append(file.stem.split(".")[0])

    for name in list(OrderedDict.fromkeys(all_stems)):
        latest_file, _ = find_latest(folder, name, extension)
        latest_files.append(latest_file)

    return latest_files


def find_latest_partial(folder, partial_name, extension):
    # type: (Path, str, str) -> Tuple[Optional[Path], int]
    """Finds the latest file that contains the partial_name and extension."""
    latest = None
    latest_version = -1

    folder = Path.validate_path(folder)

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
    
    folder = Path.validate_path(folder)
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
    folder = Path.validate_path(folder)

    latest, latest_version = find_latest(folder=folder, versioned_name=versioned_name, extension=extension)

    if not latest:
        latest = folder.resolve(strict=False) / "dummy_file"
        latest_version = 0

    new_version = latest_version + 1
    new_path = latest.parent / f"{versioned_name}.v{new_version:03d}.{extension}"

    return (new_path, new_version)

def get_files_by_extension(folder, extension):
    # type: (Path, str) -> List[Path]
    path = Path.validate_path(folder)
    if path is None:
        return None
    
    files = list(path.glob(f"*.{extension}"))

    return files

def find_versioned_files(folder):
    # type: (Path) -> List[Path]
    folder_path = Path.validate_path(folder)
    if folder_path is None:
        return None
    
    file_paths = folder_path.iterdir()

    return sorted(file_paths, key=lambda path: path.version)