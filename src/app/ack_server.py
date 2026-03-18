from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.config import Settings


ACK_SERVER_HOST = "127.0.0.1"
ACK_SERVER_BASE_PORT = 48700
ACK_SERVER_PORT_SPAN = 1000


def ack_server_port(profile_name: str) -> int:
    return ACK_SERVER_BASE_PORT + (sum(profile_name.encode("utf-8")) % ACK_SERVER_PORT_SPAN)


def acknowledgement_url(settings: Settings, *, card_id: int) -> str:
    query = urllib.parse.urlencode(
        {
            "profile": settings.profile_name,
            "card_id": card_id,
        }
    )
    return f"http://{ACK_SERVER_HOST}:{ack_server_port(settings.profile_name)}/ack?{query}"


def ensure_ack_server(settings: Settings) -> None:
    if _is_server_healthy(settings):
        return

    log_path = Path("/tmp") / f"vn.{settings.profile_name}.ack-server.log"
    log_handle = log_path.open("a", encoding="utf-8")
    python_path = os.environ.get("PYTHONPATH")
    project_python_path = str(settings.project_root / "src")
    merged_python_path = (
        f"{project_python_path}{os.pathsep}{python_path}" if python_path else project_python_path
    )

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "app.cli",
            "--profile",
            settings.profile_name,
            "serve-ack-server",
        ],
        cwd=settings.project_root,
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
        env={
            **os.environ,
            "PYTHONPATH": merged_python_path,
        },
    )

    deadline = time.time() + 2.0
    while time.time() < deadline:
        if _is_server_healthy(settings):
            return
        time.sleep(0.1)


def _is_server_healthy(settings: Settings) -> bool:
    url = f"http://{ACK_SERVER_HOST}:{ack_server_port(settings.profile_name)}/health"
    try:
        with urllib.request.urlopen(url, timeout=0.3) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False
