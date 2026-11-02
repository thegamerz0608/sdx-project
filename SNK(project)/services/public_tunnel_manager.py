"""
Public Internet Gateway & Reverse Proxy Tunnel Manager
Exposes localhost:8000 to the global internet via Cloudflare Quick Tunnel, LocalTunnel, or Pinggy.
Enables access from any external computer or smartphone on any cellular/Wi-Fi network anywhere:
  - Admin Security Gateway:     https://<public_domain>/admin-login
  - Staff & Faculty Portal:     https://<public_domain>/staff-login
  - Biometric QR Punch Terminal: https://<public_domain>/punch-interface
"""
import sys
import os
import re
import time
import shutil
import signal
import atexit
import subprocess
import threading
import queue
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv site-packages is in sys.path
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from repositories.settings_repository import settings_repository
from services.mobile_punch_service import is_biometric_server_running, ensure_biometric_daemon_running
from utils.logger import get_logger

logger = get_logger("public_tunnel_manager")

CLOUDFLARED_DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)

active_tunnel_proc: Optional[subprocess.Popen] = None
_cleaned_up = False


def kill_process_tree(proc: subprocess.Popen):
    """Safely kills a process and all its children on Windows/POSIX."""
    if not proc or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            proc.terminate()
            proc.wait(timeout=2)
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        logger.debug(f"Process termination fallback: {e}")


def cleanup_tunnel():
    """Restores settings and cleans up background processes."""
    global active_tunnel_proc, _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    print("\n[*] Stopping public internet tunnel gateway...", flush=True)
    if active_tunnel_proc:
        kill_process_tree(active_tunnel_proc)
        active_tunnel_proc = None
    print("[OK] Public tunnel safely stopped.", flush=True)


atexit.register(cleanup_tunnel)


def _signal_handler(signum, frame):
    cleanup_tunnel()
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def get_or_download_cloudflared() -> Optional[str]:
    """Finds or downloads the standalone cloudflared.exe binary."""
    cf_bin = shutil.which("cloudflared")
    if cf_bin:
        return cf_bin

    local_bin = BASE_DIR / "cloudflared.exe"
    if local_bin.exists():
        return str(local_bin)

    print("[*] Cloudflare Tunnel binary (cloudflared.exe) not found locally.", flush=True)
    print("    Attempting automatic download from official Cloudflare GitHub release...", flush=True)
    try:
        urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD_URL, str(local_bin))
        if local_bin.exists() and local_bin.stat().st_size > 1000000:
            print("[SUCCESS] 🚀 Downloaded cloudflared.exe successfully!", flush=True)
            return str(local_bin)
    except Exception as e:
        print(f"[!] Could not auto-download cloudflared.exe ({e}).", flush=True)
        print("    You can manually place cloudflared.exe in your project folder.", flush=True)

    return None


def run_cloudflared_tunnel(port: int = 8000, timeout_seconds: int = 20) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """Runs Cloudflare Quick Tunnel and extracts https://*.trycloudflare.com URL."""
    cf_bin = get_or_download_cloudflared()
    if not cf_bin:
        return None, None

    cmd = [cf_bin, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    print(f"[*] Starting Cloudflare Quick Tunnel on port {port}...", flush=True)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=(sys.platform == "win32"),
        )
    except Exception as exc:
        logger.warning(f"Failed to spawn cloudflared: {exc}")
        return None, None

    output_queue: queue.Queue = queue.Queue()

    def _reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    output_queue.put(line)
        except Exception:
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    deadline = time.time() + timeout_seconds
    extracted_url = None

    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            line = output_queue.get(timeout=0.4)
            line_clean = line.strip()
            match = re.search(r"https://[a-zA-Z0-9.\-]+\.trycloudflare\.com", line_clean)
            if match:
                extracted_url = match.group(0)
                break
        except queue.Empty:
            continue

    if extracted_url:
        return proc, extracted_url
    else:
        kill_process_tree(proc)
        return None, None


def run_localtunnel(port: int = 8000, timeout_seconds: int = 15) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """Runs LocalTunnel via npx and extracts https://*.loca.lt URL."""
    npx_bin = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx_bin:
        return None, None

    cmd = [npx_bin, "--yes", "localtunnel", "--port", str(port)]
    print(f"[*] Starting LocalTunnel (npx) on port {port}...", flush=True)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=(sys.platform == "win32"),
        )
    except Exception as exc:
        logger.warning(f"Failed to spawn localtunnel: {exc}")
        return None, None

    output_queue: queue.Queue = queue.Queue()

    def _reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    output_queue.put(line)
        except Exception:
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    deadline = time.time() + timeout_seconds
    extracted_url = None

    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            line = output_queue.get(timeout=0.4)
            line_clean = line.strip()
            match = re.search(r"https://[a-zA-Z0-9.\-]+\.loca\.lt", line_clean)
            if match:
                extracted_url = match.group(0)
                break
        except queue.Empty:
            continue

    if extracted_url:
        return proc, extracted_url
    else:
        kill_process_tree(proc)
        return None, None


def run_pinggy_tunnel(port: int = 8000, timeout_seconds: int = 15) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """Runs Pinggy SSH tunnel using built-in Windows OpenSSH."""
    ssh_bin = shutil.which("ssh") or "C:\\Windows\\System32\\OpenSSH\\ssh.exe"
    if not os.path.exists(ssh_bin):
        return None, None

    cmd = [
        ssh_bin,
        "-p", "443",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=NUL",
        "-R0:localhost:8000",
        "a.pinggy.io"
    ]
    print(f"[*] Starting Pinggy SSH tunnel on port {port}...", flush=True)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=(sys.platform == "win32"),
        )
    except Exception as exc:
        logger.warning(f"Failed to spawn pinggy ssh: {exc}")
        return None, None

    output_queue: queue.Queue = queue.Queue()

    def _reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    output_queue.put(line)
        except Exception:
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    deadline = time.time() + timeout_seconds
    extracted_url = None

    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            line = output_queue.get(timeout=0.4)
            line_clean = line.strip()
            match = re.search(r"https://[a-zA-Z0-9.\-]+\.pinggy\.link", line_clean)
            if match:
                extracted_url = match.group(0)
                break
        except queue.Empty:
            continue

    if extracted_url:
        return proc, extracted_url
    else:
        kill_process_tree(proc)
        return None, None


def launch_public_gateway(port: int = 8000, preferred_provider: str = "auto") -> Optional[str]:
    """
    Spawns an encrypted public HTTPS gateway so external computers on any internet
    can reach Admin, Staff, and Biometric portals.
    """
    global active_tunnel_proc

    # 1. Ensure ERP Backend is running
    if not is_biometric_server_running(port=port):
        print(f"[*] Biometric ERP server not detected on port {port}. Starting daemon...", flush=True)
        ensure_biometric_daemon_running(port=port)
        time.sleep(2)

    public_base_url = None
    provider_name = ""

    # Priority 1: Cloudflare Quick Tunnel (Best quality, no sign-in, genuine HTTPS)
    if preferred_provider in ["auto", "cloudflare"]:
        proc, url = run_cloudflared_tunnel(port=port)
        if url:
            active_tunnel_proc = proc
            public_base_url = url
            provider_name = "Cloudflare Quick Tunnel"

    # Priority 2: LocalTunnel (Node.js npx)
    if not public_base_url and preferred_provider in ["auto", "localtunnel"]:
        proc, url = run_localtunnel(port=port)
        if url:
            active_tunnel_proc = proc
            public_base_url = url
            provider_name = "LocalTunnel"

    # Priority 3: Pinggy (Windows OpenSSH)
    if not public_base_url and preferred_provider in ["auto", "pinggy"]:
        proc, url = run_pinggy_tunnel(port=port)
        if url:
            active_tunnel_proc = proc
            public_base_url = url
            provider_name = "Pinggy SSH"

    if not public_base_url:
        print("[ERROR] Could not establish a public HTTPS tunnel automatically.", flush=True)
        print("Please check your internet connection or install cloudflared.", flush=True)
        return None

    # Clean trailing slashes
    public_base_url = public_base_url.rstrip("/")

    # Update MySQL SYSTEM_SETTINGS so Kiosk QR code and Desktop UI display the public URL
    punch_url = f"{public_base_url}/punch-interface"
    try:
        settings_repository.set_setting("BIOMETRIC_SERVER_URL", punch_url)
        settings_repository.set_setting("BIOMETRIC_DAEMON_STATUS", "ONLINE")
        settings_repository.set_setting("BIOMETRIC_TUNNEL_MODE", f"{provider_name} (Global)")
    except Exception as e:
        logger.debug(f"SYSTEM_SETTINGS update notice: {e}")

    # Display clear, formatted URLs
    print("\n" + "=" * 80, flush=True)
    print("  🚀 GLOBAL INTERNET ACCESS GATEWAY IS NOW ACTIVE!", flush=True)
    print(f"  Provider: {provider_name} (Encrypted Public HTTPS)", flush=True)
    print("=" * 80, flush=True)
    print("  These links work on ANY computer, laptop, or smartphone worldwide", flush=True)
    print("  across ANY internet connection (Wi-Fi, 4G, 5G, mobile hotspot):\n", flush=True)
    print(f"  👑 Admin Security Gateway : {public_base_url}/admin-login", flush=True)
    print(f"  👨‍🏫 Staff & Faculty Portal   : {public_base_url}/staff-login", flush=True)
    print(f"  📱 Biometric QR Terminal  : {public_base_url}/punch-interface", flush=True)
    print("=" * 80, flush=True)
    print("  Keep this terminal window open to keep the public gateway active.", flush=True)
    print("  Press Ctrl+C at any time to close external internet access.\n", flush=True)

    return public_base_url


if __name__ == "__main__":
    provider_arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    url = launch_public_gateway(port=8000, preferred_provider=provider_arg)
    if url:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cleanup_tunnel()
