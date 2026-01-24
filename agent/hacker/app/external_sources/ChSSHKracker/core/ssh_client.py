# -*- UTF-8 -*-
# core/ssh_client.py

import threading
from typing import Optional, Union

from paramiko import SSHClient, AutoAddPolicy, AuthenticationException


class SSH(SSHClient):
    def __init__(self, hostname: str, port: int, username: str, password: str, timeout: int) -> None:
        super().__init__()

        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout

        self._lock = threading.Lock()
        self._connected = False
        self.set_missing_host_key_policy(AutoAddPolicy())
    
    def connect_safe(self):
        with self._lock:
            if self._connected:
                return True
        
        try:
            self.connect(
                hostname=self._hostname, 
                port=self._port, 
                username=self._username, 
                password=self._password, 
                timeout=self._timeout, 
                allow_agent=False, 
                look_for_keys=False
                )
            with self._lock:
                self._connected = True
                return True
        except AuthenticationException:
            with self._lock:
                self._connected = False
            raise Exception('Connection Failed!')
        except Exception:
            with self._lock:
                self._connected = False
            raise Exception('Connection Failed!')
        finally:
            if 'client' in locals():
                self.close()

    def run(self, command: str, timeout: Optional[Union[int, float]] = None) -> str:
        with self._lock:
            if not self._connected:
                return "ERROR: Not connected"

            try:
                actual_timeout = timeout if timeout is not None else self._timeout
                stdin, stdout, stderr = self.exec_command(command, timeout=actual_timeout)
                out = stdout.read().decode(errors="ignore")
                err = stderr.read().decode(errors="ignore")

                if err.strip():
                    return f"ERROR: {err.strip()}"
                return out
            except Exception as exc:
                return f"ERROR: {exc}"