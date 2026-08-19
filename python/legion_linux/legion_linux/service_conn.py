"""Unprivileged client connection to the native Legion service."""
import json
import os
import socket

SOCKET_PATH = "/run/legion-linux/control.sock"
CONNECTION_TIMEOUT = 10
READ_CHUNK_SIZE = 64 * 1024


class ServiceError(RuntimeError):
    """A request to the privileged service could not be completed."""


def _receive_message(connection):
    """Read chunks until they form one complete JSON object."""
    payload = bytearray()
    while True:
        if payload:
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                value = None
            else:
                if not isinstance(value, dict):
                    raise ServiceError("JSON message must be an object")
                return value

        chunk = connection.recv(READ_CHUNK_SIZE)
        if not chunk:
            if not payload:
                raise ServiceError("empty message")
            raise ServiceError("incomplete or invalid JSON message")
        payload.extend(chunk)


def _send_message(connection, value):
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    connection.sendall(payload)


class LegionServiceClient:
    """Small synchronous client used by both unprivileged front ends."""

    def __init__(self, socket_path=None, timeout=CONNECTION_TIMEOUT):
        self.socket_path = socket_path or os.environ.get(
            "LEGION_LINUX_SOCKET", SOCKET_PATH)
        self.timeout = timeout

    def request(self, operation, **arguments):
        request = {"version": 1, "operation": operation, "arguments": arguments}
        payload = json.dumps(request, separators=(",", ":")).encode("utf-8")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(self.socket_path)
                connection.sendall(payload)
                response = _receive_message(connection)
        except PermissionError as error:
            raise ServiceError(
                "access denied; your user must be root or a member of the "
                "legion-linux group (log out and back in after joining)"
            ) from error
        except (AttributeError, OSError, ValueError, json.JSONDecodeError) as error:
            raise ServiceError(
                "legion service is unavailable; ensure legion-linux.service is running"
            ) from error
        if not response.get("ok"):
            raise ServiceError(response.get("error", "service request failed"))
        return response.get("result")
