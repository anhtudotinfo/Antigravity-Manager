# -*- coding: utf-8 -*-
import os
import sys
import platform
from pathlib import Path
from datetime import datetime

# -------------------------------------------------------------------------
# Logging utilities
# -------------------------------------------------------------------------

def get_log_file_path():
    """Get log file path"""
    try:
        log_dir = get_app_data_dir()
        return log_dir / "app.log"
    except:
        return None

def _log_to_file(message):
    """Write log to file"""
    try:
        log_file = get_log_file_path()
        if log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def _print_with_color(color_code, symbol, message):
    """Print with color and write to file"""
    formatted_msg = f"{symbol} {message}"
    # In no-console mode, sys.stdout may be None and printing would raise an error
    if sys.stdout:
        try:
            print(f"\033[{color_code}m{formatted_msg}\033[0m")
        except:
            pass
    _log_to_file(formatted_msg)

def info(message):
    """Print info log (green)"""
    _print_with_color("32", "INFO", message)

def warning(message):
    """Print warning log (yellow)"""
    _print_with_color("33", "WARN", message)

def error(message):
    """Print error log (red)"""
    _print_with_color("31", "ERR ", message)

def debug(message):
    """Print debug log (gray)"""
    # Only print when DEBUG environment variable is set
    if os.environ.get("DEBUG"):
        _print_with_color("90", "DBUG", message)
    else:
        # In packaged apps, we also want to log debug info to file for troubleshooting
        _log_to_file(f"DBUG {message}")

# -------------------------------------------------------------------------
# Path utilities
# -------------------------------------------------------------------------

def get_app_data_dir():
    """Get application data directory (~/.antigravity-agent)"""
    home = Path.home()
    config_dir = home / ".antigravity-agent"
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_accounts_file_path():
    """Get accounts storage file path"""
    return get_app_data_dir() / "antigravity_accounts.json"

def get_antigravity_db_paths():
    """Get possible Antigravity database paths"""
    system = platform.system()
    paths = []
    home = Path.home()

    if system == "Darwin":  # macOS
        # Standard path: ~/Library/Application Support/Antigravity/User/globalStorage/state.vscdb
        paths.append(home / "Library/Application Support/Antigravity/User/globalStorage/state.vscdb")
        # Alternate path (older versions)
        paths.append(home / "Library/Application Support/Antigravity/state.vscdb")
    elif system == "Windows":
        # Standard path: %APPDATA%/Antigravity/state.vscdb
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_path = Path(appdata) / "Antigravity"
            paths.append(base_path / "User/globalStorage/state.vscdb")
            paths.append(base_path / "User/state.vscdb")
            paths.append(base_path / "state.vscdb")
    elif system == "Linux":
        # Standard path: ~/.config/Antigravity/User/globalStorage/state.vscdb
        paths.append(home / ".config/Antigravity/User/globalStorage/state.vscdb")
        # Alternate path (older versions)
        paths.append(home / ".config/Antigravity/state.vscdb")

    return paths

def get_antigravity_executable_path():
    """Get Antigravity executable path"""
    system = platform.system()

    if system == "Darwin":
        return Path("/Applications/Antigravity.app/Contents/MacOS/Antigravity")
    elif system == "Windows":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
        program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))

        possible_paths = [
            local_app_data / "Programs/Antigravity/Antigravity.exe",
            program_files / "Antigravity/Antigravity.exe",
            program_files_x86 / "Antigravity/Antigravity.exe"
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Fallback to default if nothing found (though likely won't exist)
        return local_app_data / "Programs/Antigravity/Antigravity.exe"

    elif system == "Linux":
        return Path("/usr/share/antigravity/antigravity")

    return None

def open_uri(uri):
    """Open URI protocol cross-platform

    Args:
        uri: The URI to open, e.g. "antigravity://oauth-success"

    Returns:
        bool: Whether the launch was successful
    """
    import subprocess
    system = platform.system()

    try:
        if system == "Darwin":
            # macOS: Use open command
            subprocess.Popen(["open", uri])
        elif system == "Windows":
            # Windows: Use start command
            # CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False, creationflags=0x08000000)
        elif system == "Linux":
            # Linux: Use xdg-open
            subprocess.Popen(["xdg-open", uri])
        else:
            error(f"Unsupported operating system: {system}")
            return False

        return True
    except Exception as e:
        error(f"Failed to open URI: {e}")
        return False
