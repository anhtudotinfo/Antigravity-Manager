# -*- coding: utf-8 -*-
import os
import time
import platform
import subprocess
import psutil

# Use relative imports
from utils import info, error, warning, get_antigravity_executable_path, open_uri

def is_process_running(process_name=None):
    """Check if the Antigravity process is running

    Uses cross-platform detection:
    - macOS: Check if path contains Antigravity.app
    - Windows: Check process name or path contains antigravity
    - Linux: Check process name or path contains antigravity
    """
    system = platform.system()

    for proc in psutil.process_iter(['name', 'exe']):
        try:
            process_name_lower = proc.info['name'].lower() if proc.info['name'] else ""
            exe_path = proc.info.get('exe', '').lower() if proc.info.get('exe') else ""

            # Cross-platform detection
            is_antigravity = False

            if system == "Darwin":
                # macOS: Check if path contains Antigravity.app
                is_antigravity = 'antigravity.app' in exe_path
            elif system == "Windows":
                # Windows: Check process name or path contains antigravity
                is_antigravity = (process_name_lower in ['antigravity.exe', 'antigravity'] or
                                 'antigravity' in exe_path)
            else:
                # Linux: Check process name or path contains antigravity
                is_antigravity = (process_name_lower == 'antigravity' or
                                 'antigravity' in exe_path)

            if is_antigravity:
                return True

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def close_antigravity(timeout=10, force_kill=True):
    """Gracefully close all Antigravity processes

    Shutdown strategy (three phases, cross-platform):
    1. Platform-specific graceful exit
       - macOS: AppleScript
       - Windows: taskkill /IM (graceful termination)
       - Linux: SIGTERM
    2. Gentle termination (SIGTERM/TerminateProcess) - give process time to clean up
    3. Force kill (SIGKILL/taskkill /F) - last resort
    """
    info("Attempting to close Antigravity...")
    system = platform.system()

    # Platform check
    if system not in ["Darwin", "Windows", "Linux"]:
        warning(f"Unknown platform: {system}, will try generic method")

    try:
        # Phase 1: Platform-specific graceful exit
        if system == "Darwin":
            # macOS: Use AppleScript
            info("Attempting graceful exit via AppleScript...")
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "Antigravity" to quit'],
                    capture_output=True,
                    timeout=3
                )
                if result.returncode == 0:
                    info("Quit request sent, waiting for app to respond...")
                    time.sleep(2)
            except Exception as e:
                warning(f"AppleScript quit failed: {e}, will use other methods")

        elif system == "Windows":
            # Windows: Use taskkill for graceful termination (without /F flag)
            info("Attempting graceful exit via taskkill...")
            try:
                # CREATE_NO_WINDOW = 0x08000000
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                result = subprocess.run(
                    ["taskkill", "/IM", "Antigravity.exe", "/T"],
                    capture_output=True,
                    timeout=3,
                    creationflags=0x08000000
                )
                if result.returncode == 0:
                    info("Quit request sent, waiting for app to respond...")
                    time.sleep(2)
            except Exception as e:
                warning(f"taskkill quit failed: {e}, will use other methods")

        # Linux doesn't need special handling, uses SIGTERM directly

        # Check and collect processes still running
        target_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                process_name_lower = proc.info['name'].lower() if proc.info['name'] else ""
                exe_path = proc.info.get('exe', '').lower() if proc.info.get('exe') else ""

                # Exclude self process
                if proc.pid == os.getpid():
                    continue

                # Exclude all processes in current app directory (prevent killing self and child processes)
                # In PyInstaller packaged environment, sys.executable points to the exe file
                # In development environment, it points to python.exe
                try:
                    import sys
                    current_exe = sys.executable
                    current_dir = os.path.dirname(os.path.abspath(current_exe)).lower()
                    if exe_path and current_dir in exe_path:
                        continue
                except:
                    pass

                # Cross-platform detection: check process name or executable path
                is_antigravity = False

                if system == "Darwin":
                    # macOS: Check if path contains Antigravity.app
                    is_antigravity = 'antigravity.app' in exe_path
                elif system == "Windows":
                    # Windows: Strict match process name antigravity.exe
                    # Or path contains antigravity and process name is not Antigravity Manager.exe
                    is_target_name = process_name_lower in ['antigravity.exe', 'antigravity']
                    is_in_path = 'antigravity' in exe_path
                    is_manager = 'manager' in process_name_lower

                    is_antigravity = is_target_name or (is_in_path and not is_manager)
                else:
                    # Linux: Check process name or path contains antigravity
                    is_antigravity = (process_name_lower == 'antigravity' or
                                     'antigravity' in exe_path)

                if is_antigravity:
                    info(f"Found target process: {proc.info['name']} ({proc.pid}) - {exe_path}")
                    target_processes.append(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not target_processes:
            info("All Antigravity processes have been closed")
            return True

        info(f"Detected {len(target_processes)} process(es) still running")

        # Phase 2: Gently request process termination (SIGTERM)
        info("Sending termination signal (SIGTERM)...")
        for proc in target_processes:
            try:
                if proc.is_running():
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                continue
            except Exception as e:
                continue

        # Wait for processes to terminate naturally
        info(f"Waiting for processes to exit (up to {timeout} seconds)...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            still_running = []
            for proc in target_processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not still_running:
                info("All Antigravity processes have been closed")
                return True

            time.sleep(0.5)

        # Phase 3: Force kill stubborn processes (SIGKILL)
        if still_running:
            still_running_names = ", ".join([f"{p.info['name']}({p.pid})" for p in still_running])
            warning(f"{len(still_running)} process(es) still running: {still_running_names}")

            if force_kill:
                info("Sending force kill signal (SIGKILL)...")
                for proc in still_running:
                    try:
                        if proc.is_running():
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Final check
                time.sleep(1)
                final_check = []
                for proc in still_running:
                    try:
                        if proc.is_running():
                            final_check.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if not final_check:
                    info("All Antigravity processes have been terminated")
                    return True
                else:
                    final_list = ", ".join([f"{p.info['name']}({p.pid})" for p in final_check])
                    error(f"Unable to terminate processes: {final_list}")
                    return False
            else:
                error("Some processes could not be closed, please close them manually and retry")
                return False

        return True

    except Exception as e:
        error(f"Error while closing Antigravity processes: {str(e)}")
        return False

def start_antigravity(use_uri=True):
    """Start Antigravity

    Args:
        use_uri: Whether to use URI protocol to launch (default True)
                 URI protocol is more reliable and doesn't need executable path lookup
    """
    info("Starting Antigravity...")
    system = platform.system()

    try:
        # Prefer URI protocol launch (cross-platform)
        if use_uri:
            info("Launching via URI protocol...")
            uri = "antigravity://oauth-success"

            if open_uri(uri):
                info("Antigravity URI launch command sent")
                return True
            else:
                warning("URI launch failed, trying executable path...")
                # Continue with fallback below

        # Fallback: Launch using executable path
        info("Launching via executable path...")
        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Antigravity"])
        elif system == "Windows":
            path = get_antigravity_executable_path()
            if path and path.exists():
                # CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen([str(path)], creationflags=0x08000000)
            else:
                error("Antigravity executable not found")
                warning("Hint: Try using URI protocol to launch (use_uri=True)")
                return False
        elif system == "Linux":
            subprocess.Popen(["antigravity"])

        info("Antigravity launch command sent")
        return True
    except Exception as e:
        error(f"Error starting process: {e}")
        # If URI launch failed, try executable path
        if use_uri:
            warning("URI launch failed, trying executable path...")
            return start_antigravity(use_uri=False)
        return False
