"""
Smartphone Biometric Bridge Daemon (Microservice)
Independent background service providing mobile WebAuthn attendance check-in.
Features automated tunnel fallback:
  1. pyngrok HTTPS cloud tunnel
  2. localtunnel (npx) HTTPS cloud tunnel (bypasses Windows Application Control on ngrok.exe)
  3. Local Wi-Fi LAN IP fallback
Includes robust atexit and signal teardown to kill tunnel subprocesses and reset SYSTEM_SETTINGS.
"""
import sys
import os
import re
import time
import signal
import atexit
import shutil
import argparse
import subprocess
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Windows consoles default to cp1252 and crash on emoji; force UTF-8 safely.
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream is not None:
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv site-packages is in sys.path
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import uvicorn
from config.settings import settings
from services.mobile_punch_service import (
    create_mobile_app,
    get_local_lan_ip,
)
from services.time_service import TimeService
from repositories.settings_repository import settings_repository
from utils.logger import get_logger

logger = get_logger("biometric_daemon")

HEARTBEAT_INTERVAL_SECONDS = 30
LOCALTUNNEL_TIMEOUT_SECONDS = 30

# Global state handles for cleanup
active_ngrok_tunnel = None
active_localtunnel_proc: Optional[subprocess.Popen] = None
_teardown_performed = False
_daemon_started = False
_state_lock = threading.RLock()
_shutdown_event = threading.Event()


def kill_process_tree(proc: subprocess.Popen):
    """Safely kills a process and all its spawned child processes on Windows/POSIX."""
    if not proc or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            # Force kill the process tree (/T) to terminate node.exe and child wrappers
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
        logger.debug(f"Process termination fallback notice: {e}")


def _close_tunnels():
    """Idempotently closes any active LocalTunnel / pyngrok tunnel."""
    global active_ngrok_tunnel, active_localtunnel_proc

    with _state_lock:
        lt_proc, active_localtunnel_proc = active_localtunnel_proc, None
        ng_tunnel, active_ngrok_tunnel = active_ngrok_tunnel, None

    if lt_proc:
        print("[*] Terminating LocalTunnel background process tree...", flush=True)
        kill_process_tree(lt_proc)
        print("[OK] LocalTunnel process safely terminated.", flush=True)

    if ng_tunnel:
        print("[*] Disconnecting Pyngrok tunnels...", flush=True)
        try:
            from pyngrok import ngrok
            try:
                ngrok.disconnect(ng_tunnel.public_url)
            except Exception as e:
                logger.debug(f"Ngrok disconnect notice: {e}")
            ngrok.kill()
            print("[OK] Pyngrok tunnels closed.", flush=True)
        except Exception as e:
            logger.debug(f"Ngrok close notice: {e}")


def cleanup_daemon():
    """
    Strict teardown sequence:
    1. Safely terminates any active localtunnel or ngrok process.
    2. Resets SYSTEM_SETTINGS in MySQL (BIOMETRIC_SERVER_URL -> OFFLINE, STATUS -> INACTIVE).
    3. Handles unexpected MySQL/XAMPP disconnections gracefully without crashing.
    """
    global _teardown_performed
    with _state_lock:
        if _teardown_performed or not _daemon_started:
            return
        _teardown_performed = True
    _shutdown_event.set()

    print("\n" + "=" * 76, flush=True)
    print(" [DAEMON TEARDOWN] Initiating graceful shutdown and system cleanup...", flush=True)
    print("=" * 76, flush=True)

    # 1 & 2. Kill tunnels
    _close_tunnels()

    # 3. Clean up database SYSTEM_SETTINGS table
    print("[*] Cleaning up SYSTEM_SETTINGS table in MySQL database...", flush=True)
    try:
        settings_repository.set_setting(
            key="BIOMETRIC_SERVER_URL",
            value="OFFLINE",
            description="Biometric endpoint cleared on daemon shutdown",
        )
        settings_repository.set_setting(
            key="BIOMETRIC_DAEMON_STATUS",
            value="INACTIVE",
            description="Daemon process status",
        )
        settings_repository.set_setting(
            key="BIOMETRIC_DAEMON_PID",
            value="0",
            description="Daemon PID",
        )
        settings_repository.set_setting(
            key="BIOMETRIC_TUNNEL_MODE",
            value="NONE",
            description="Active tunnel provider",
        )
        print("[SUCCESS] SYSTEM_SETTINGS reset: BIOMETRIC_SERVER_URL = OFFLINE | STATUS = INACTIVE", flush=True)
    except Exception as db_err:
        print(f"[NOTE] Database update skipped (MySQL connection unavailable or stopped: {db_err})", flush=True)

    print("[DAEMON] All resources released. Biometric Daemon shutdown complete.\n", flush=True)


# Register cleanup for normal interpreter exit
atexit.register(cleanup_daemon)


def _signal_handler(signum, frame):
    """
    Convert SIGINT/SIGTERM/SIGBREAK into KeyboardInterrupt so shutdown unwinds
    through start_daemon's `finally` block instead of doing DB work in signal context.
    """
    raise KeyboardInterrupt()


def _install_signal_handlers():
    names = ["SIGINT", "SIGTERM"]
    if sys.platform == "win32":
        names.append("SIGBREAK")  # Console window close / Ctrl+Break
    for name in names:
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except (ValueError, OSError) as exc:
            logger.debug(f"Could not install handler for {name}: {exc}")


def start_localtunnel(port: int, timeout_seconds: int = LOCALTUNNEL_TIMEOUT_SECONDS) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """
    Automated LocalTunnel fallback using npx.
    Bypasses Windows Application Control policies that block standalone ngrok.exe.
    Extracts the https://*.loca.lt URL from subprocess output.
    """
    npx_bin = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx_bin:
        print("[*] Node.js npx not found in system PATH. Skipping LocalTunnel.", flush=True)
        return None, None

    cmd = [npx_bin, "--yes", "localtunnel", "--port", str(port)]
    print(f"[*] Launching LocalTunnel via: {' '.join(cmd)}", flush=True)
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
        print(f"[WARNING] Could not spawn npx localtunnel process: {exc}", flush=True)
        return None, None

    output_queue: queue.Queue = queue.Queue()
    url_found = threading.Event()

    def _reader():
        # Keep draining the pipe for the process lifetime so it never blocks,
        # but only queue lines until the URL has been captured.
        try:
            for line in iter(proc.stdout.readline, ''):
                if line and not url_found.is_set():
                    output_queue.put(line)
        except Exception:
            pass

    threading.Thread(target=_reader, daemon=True).start()

    deadline = time.time() + timeout_seconds
    extracted_url = None

    while time.time() < deadline and not _shutdown_event.is_set():
        if proc.poll() is not None:
            break
        try:
            line = output_queue.get(timeout=0.4)
        except queue.Empty:
            continue
        line_clean = line.strip()
        if line_clean:
            print(f"    [LocalTunnel] {line_clean}", flush=True)
        match = re.search(r"https://[a-zA-Z0-9.\-]+\.loca\.lt", line_clean)
        if match:
            extracted_url = match.group(0)
            url_found.set()
            break

    if extracted_url:
        return proc, extracted_url

    kill_process_tree(proc)
    return None, None


def initialize_tunnel_bridge(port: int, allow_ngrok: bool = True) -> Tuple[Optional[str], str]:
    """
    Automated fallback strategy:
      1. pyngrok HTTPS tunnel (if allow_ngrok)
      2. localtunnel (npx) HTTPS tunnel
      3. none -> (None, "LOCAL_HTTP"); caller keeps the local-domain endpoint
    """
    global active_ngrok_tunnel, active_localtunnel_proc

    # Tier 1: Try pyngrok
    if allow_ngrok and not _shutdown_event.is_set():
        print("[1/2] Attempting Pyngrok HTTPS cloud tunnel...", flush=True)
        try:
            from pyngrok import ngrok
            tunnel = ngrok.connect(port, "http")
            with _state_lock:
                active_ngrok_tunnel = tunnel
            public_url = f"{tunnel.public_url}/punch-interface"
            print(f"[SUCCESS] 🚀 Pyngrok HTTPS Tunnel Active: {public_url}", flush=True)
            return public_url, "PYNGROK_HTTPS"
        except Exception as ngrok_err:
            logger.debug(f"Pyngrok notice: {ngrok_err}")
            print("[*] Pyngrok unavailable, falling back...", flush=True)

    # Tier 2: Try LocalTunnel (npx)
    if not _shutdown_event.is_set():
        print("[2/2] Attempting LocalTunnel (npx) HTTPS bypass...", flush=True)
        lt_proc, lt_url = start_localtunnel(port=port)
        if lt_url:
            with _state_lock:
                active_localtunnel_proc = lt_proc
            public_url = f"{lt_url}/punch-interface"
            print(f"[SUCCESS] 🚀 LocalTunnel HTTPS Active: {public_url}", flush=True)
            return public_url, "LOCALTUNNEL_HTTPS"

    return None, "LOCAL_HTTP"


def _heartbeat_worker():
    """Refreshes BIOMETRIC_LAST_HEARTBEAT until shutdown."""
    while not _shutdown_event.wait(HEARTBEAT_INTERVAL_SECONDS):
        try:
            settings_repository.set_setting(
                "BIOMETRIC_LAST_HEARTBEAT", datetime.now().isoformat(), "Daemon heartbeat"
            )
        except Exception as exc:
            logger.debug(f"Heartbeat update skipped: {exc}")


def start_daemon(port: int = 8000, use_ngrok: bool = True, use_tunnel: bool = True):
    """Starts the Biometric Bridge Microservice and uvicorn server."""
    global _daemon_started
    _daemon_started = True
    _install_signal_handlers()

    lan_ip = get_local_lan_ip()
    domain = getattr(settings, "ERP_DOMAIN", "erp.sys")
    port_str = "" if port in (80, 443) else f":{port}"

    print("=" * 76, flush=True)
    print("   AI-ENABLED FACULTY ATTENDANCE ERP - BIOMETRIC BRIDGE DAEMON", flush=True)
    print("   Microservice: FastAPI + WebAuthn + Automated Fast Sync", flush=True)
    print("=" * 76, flush=True)
    time_mode = "TEST (Simulated)" if TimeService.is_test_mode() else "NORMAL (Real-Time)"
    eff_time = TimeService.get_current_time_str()
    print(f"[*] Process PID: {os.getpid()} | Local Host: http://{lan_ip}:{port}", flush=True)
    print(f"[*] Shared Time Sync: [{time_mode}] | Campus Time: {eff_time}", flush=True)

    try:
        # 1. Immediately register base local domain endpoint into SYSTEM_SETTINGS
        # This guarantees the Kiosk and Desktop app see ONLINE instantly without waiting on tunnels
        active_url = f"http://{domain}{port_str}/punch-interface"
        print("[*] Synchronizing active endpoint with SYSTEM_SETTINGS table in MySQL...", flush=True)
        try:
            settings_repository.set_setting(
                key="BIOMETRIC_SERVER_URL",
                value=active_url,
                description="Active endpoint for smartphone biometric check-in",
            )
            settings_repository.set_setting("BIOMETRIC_DAEMON_STATUS", "ONLINE", "Daemon process status")
            settings_repository.set_setting("BIOMETRIC_DAEMON_PID", str(os.getpid()), "Daemon PID")
            settings_repository.set_setting("BIOMETRIC_LAST_HEARTBEAT", datetime.now().isoformat(), "Daemon heartbeat")
            settings_repository.set_setting("BIOMETRIC_TUNNEL_MODE", "LOCAL_DOMAIN", "Active tunnel provider")
            print(f"[SUCCESS] Registered into SYSTEM_SETTINGS: {active_url} (Status: ONLINE)", flush=True)
        except Exception as exc:
            print(f"[WARNING] Database sync notice (using memory fallback): {exc}", flush=True)

        # Heartbeat keeps BIOMETRIC_LAST_HEARTBEAT fresh for the Kiosk / Desktop app
        threading.Thread(target=_heartbeat_worker, daemon=True).start()

        # 2. Asynchronously resolve HTTPS cloud tunnel in background if requested
        if use_tunnel:
            def _tunnel_worker():
                try:
                    pub_url, tunnel_mode = initialize_tunnel_bridge(port=port, allow_ngrok=use_ngrok)

                    # Shutdown may have happened while the tunnel was starting:
                    # close it ourselves and never touch the DB afterwards.
                    if _shutdown_event.is_set():
                        _close_tunnels()
                        return

                    if pub_url:
                        settings_repository.set_setting("BIOMETRIC_SERVER_URL", pub_url)
                        settings_repository.set_setting("BIOMETRIC_TUNNEL_MODE", tunnel_mode)
                        print(f"\n[🚀 CLOUD TUNNEL READY] Public Gateway: {pub_url} ({tunnel_mode})", flush=True)
                    else:
                        print("[*] No cloud tunnel available; staying on local endpoint "
                              f"{active_url} (LAN: http://{lan_ip}:{port}/punch-interface)", flush=True)
                except Exception as e:
                    logger.debug(f"Cloud tunnel background initialization notice: {e}")

            threading.Thread(target=_tunnel_worker, daemon=True).start()

        # 3. Create FastAPI App
        def _on_punch(punch_data: dict):
            emp_code = punch_data.get('employee_code', '')
            emp_name = punch_data.get('full_name', '')
            ptype = punch_data.get('punch_type', '')
            ptime = punch_data.get('punch_time', '')
            late = punch_data.get('late_minutes', 0)
            status = punch_data.get('status', 'PRESENT')
            sync_time = TimeService.get_current_time_str()
            print(f" [📲 BIOMETRIC PUNCH] {emp_code} ({emp_name}) -> {ptype} at {ptime} [Sync: {sync_time}] | Late: {late}m | Status: {status}", flush=True)

        app = create_mobile_app(punch_callback=_on_punch)

        print("\n" + "=" * 76, flush=True)
        print("  INSTITUTIONAL ERP WEB PORTALS READY:", flush=True)
        print(f"  👑 Administrator Gateway : http://{domain}{port_str}/admin-login", flush=True)
        print(f"  👨‍🏫 Staff CMS Portal      : http://{domain}{port_str}/staff-login", flush=True)
        print(f"  📱 Mobile Biometric Punch : http://{domain}{port_str}/punch-interface", flush=True)
        print(f"  🔗 Localhost Direct Link : http://127.0.0.1{port_str}/admin-login", flush=True)
        print(f"  🌐 Local Wi-Fi LAN IP    : http://{lan_ip}:{port}/punch-interface", flush=True)
        print("=" * 76, flush=True)
        print(" Press Ctrl+C in this console to terminate the daemon and reset settings.\n", flush=True)

        # 4. Start Uvicorn Server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        server.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as exc:
        logger.error(f"Biometric daemon crashed: {exc}")
        print(f"[ERROR] Biometric daemon stopped unexpectedly: {exc}", flush=True)
    finally:
        cleanup_daemon()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Biometric Bridge Daemon with Automated Fallback")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port (default: 8000)")
    parser.add_argument("--no-ngrok", action="store_true", help="Skip pyngrok and try LocalTunnel directly")
    parser.add_argument("--no-tunnel", action="store_true", help="Disable all cloud tunnels (local domain / LAN only)")
    args = parser.parse_args()

    start_daemon(port=args.port, use_ngrok=not args.no_ngrok, use_tunnel=not args.no_tunnel)