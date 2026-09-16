from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path


class AssistantDesktopLaunchError(RuntimeError):
    pass


class AssistantDesktopLauncher:
    """Launch the sandboxed Electron presentation shell.

    This infrastructure component knows how to spawn the local desktop renderer only.
    It has no provider credential, prompt, database, or character-state authority.
    """

    def __init__(self, shell_dir: Path) -> None:
        self._shell_dir = shell_dir
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        return self._electron_command() is not None

    def launch(self, *, base_url: str, session_token: str) -> None:
        with self._lock:
            command = self._electron_command()
            if command is None:
                raise AssistantDesktopLaunchError(
                    "Virtual Assistant desktop runtime is not installed. Close Protean and run install.bat again."
                )
            self._terminate_locked()
            env = os.environ.copy()
            env["PROTEAN_ASSISTANT_BASE_URL"] = base_url.rstrip("/")
            env["PROTEAN_ASSISTANT_TOKEN"] = session_token
            try:
                self._process = subprocess.Popen(
                    [str(command), str(self._shell_dir)],
                    cwd=str(self._shell_dir),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    close_fds=True,
                )
            except OSError as exc:
                self._process = None
                raise AssistantDesktopLaunchError("Could not start the Virtual Assistant desktop window") from exc

    def shutdown(self) -> None:
        with self._lock:
            self._terminate_locked()

    def _terminate_locked(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def _electron_command(self) -> Path | None:
        if sys.platform == "win32":
            candidate = self._shell_dir / "node_modules" / "electron" / "dist" / "electron.exe"
        else:
            candidate = self._shell_dir / "node_modules" / ".bin" / "electron"
        return candidate if candidate.exists() else None
