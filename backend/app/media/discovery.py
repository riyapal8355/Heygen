"""Discovery utility for external media binaries (ffmpeg and ffprobe).

Locates executables using PATH and known platform-specific installation directories
(such as Windows WinGet packages and common system directories).
"""

import glob
import os
import shutil
from typing import Optional


def find_media_binary(binary_name: str, explicit_path: Optional[str] = None) -> Optional[str]:
    """Resolve an external media binary across configured path, PATH, and known install roots.

    Args:
        binary_name: Base binary name without extension (e.g. 'ffmpeg', 'ffprobe').
        explicit_path: Optional configured path (may be exact binary path or bare command name).

    Returns:
        Absolute string path to executable if found, or None.
    """
    # 1. If an explicit path was provided and is not just the bare command name or None
    if explicit_path and explicit_path not in (binary_name, f"{binary_name}.exe"):
        resolved = shutil.which(explicit_path)
        if resolved:
            return resolved
        if os.path.exists(explicit_path) and not os.path.isdir(explicit_path):
            return os.path.abspath(explicit_path)
        # An explicit non-default path was specified and was not found
        return None

    # 2. Check standard system PATH
    found = shutil.which(binary_name)
    if found:
        return found

    # 3. On Windows, search WinGet packages, Links, and common program paths
    if os.name == "nt":
        # Check WinGet links / packages
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            link_path = os.path.join(local_app_data, "Microsoft", "WinGet", "Links", f"{binary_name}.exe")
            if os.path.exists(link_path):
                return link_path

            pkg_pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "**", f"{binary_name}.exe")
            matches = glob.glob(pkg_pattern, recursive=True)
            if matches:
                return matches[0]

        # Check standard Program Files / drive roots
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        common_locations = [
            os.path.join(program_files, "ffmpeg", "bin", f"{binary_name}.exe"),
            os.path.join(r"C:\ffmpeg", "bin", f"{binary_name}.exe"),
            os.path.join(program_files, f"{binary_name}.exe"),
        ]
        for loc in common_locations:
            if os.path.exists(loc):
                return loc

    return None
