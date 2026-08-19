import os
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legion_linux.service_conn import (
    READ_CHUNK_SIZE, LegionServiceClient, ServiceError,
    _receive_message, _send_message,
)


class FragmentingSocket:
    def __init__(self, payload, fragment_size=1):
        self.payload = payload
        self.fragment_size = fragment_size

    def recv(self, length):
        take = min(length, self.fragment_size, len(self.payload))
        result = self.payload[:take]
        self.payload = self.payload[take:]
        return result


class ProtocolFramingTests(unittest.TestCase):
    def test_fragmented_dynamic_json_is_read_until_object_is_complete(self):
        value = {"version": 1, "operation": "feature.get",
                 "arguments": {"name": "FnLockFeature"}}
        payload = json.dumps(value).encode("utf-8")
        self.assertEqual(value, _receive_message(FragmentingSocket(payload)))

    def test_incomplete_message_is_rejected_at_eof(self):
        with self.assertRaisesRegex(ServiceError, "incomplete or invalid"):
            _receive_message(FragmentingSocket(b'{"version":', 3))

    def test_message_larger_than_former_limit_is_received(self):
        value = {"value": "x" * (2 * 1024 * 1024 + READ_CHUNK_SIZE)}
        payload = json.dumps(value).encode("utf-8")
        self.assertEqual(
            value, _receive_message(FragmentingSocket(payload, READ_CHUNK_SIZE)))

    def test_large_response_is_sent_without_an_aggregate_limit(self):
        sender, receiver = socket.socketpair()
        try:
            value = {"value": "x" * (2 * 1024 * 1024 + READ_CHUNK_SIZE)}
            receiver_thread_result = []
            receiver_thread = threading.Thread(
                target=lambda: receiver_thread_result.append(
                    _receive_message(receiver)))
            receiver_thread.start()
            _send_message(sender, value)
            receiver_thread.join(timeout=5)
            self.assertFalse(receiver_thread.is_alive())
            self.assertEqual([value], receiver_thread_result)
        finally:
            sender.close()
            receiver.close()

    def test_overlapping_fragmented_connections_reassemble_their_own_chunks(self):
        senders = []
        receivers = []
        for _ in range(2):
            sender, receiver = socket.socketpair()
            senders.append(sender)
            receivers.append(receiver)
        values = [
            {"connection": 1, "value": "first" * 20000},
            {"connection": 2, "value": "second" * 20000},
        ]
        payloads = [json.dumps(value).encode("utf-8") for value in values]
        results = [None, None]
        threads = [
            threading.Thread(
                target=lambda index=index: results.__setitem__(
                    index, _receive_message(receivers[index])))
            for index in range(2)
        ]
        try:
            for thread in threads:
                thread.start()
            split = READ_CHUNK_SIZE // 2
            senders[0].sendall(payloads[0][:split])
            senders[1].sendall(payloads[1][:split])
            senders[1].sendall(payloads[1][split:])
            senders[0].sendall(payloads[0][split:])
            for thread in threads:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
            self.assertEqual(values, results)
        finally:
            for connection in senders + receivers:
                connection.close()

    def test_empty_invalid_and_non_object_messages_are_rejected(self):
        for payload in (b"", b"not json", b"[]", b'"value"'):
            with self.subTest(payload=payload):
                with self.assertRaises(ServiceError):
                    _receive_message(FragmentingSocket(payload))

    def test_sender_writes_plain_json_without_a_length_header(self):
        sender, receiver = socket.socketpair()
        try:
            _send_message(sender, {"ok": True})
            self.assertEqual(b'{"ok":true}', receiver.recv(64))
        finally:
            sender.close()
            receiver.close()


class ClientFailureTests(unittest.TestCase):
    def test_missing_service_has_actionable_error(self):
        client = LegionServiceClient("/definitely/missing/legion.sock")
        with self.assertRaisesRegex(ServiceError, "service is unavailable"):
            client.request("feature.get", name="FnLockFeature")

    @mock.patch("legion_linux.service_conn.socket.AF_UNIX", 1, create=True)
    @mock.patch("legion_linux.service_conn.socket.socket")
    def test_permission_denied_explains_required_group(self, socket_factory):
        connection = socket_factory.return_value.__enter__.return_value
        connection.connect.side_effect = PermissionError(13, "Permission denied")
        with self.assertRaisesRegex(ServiceError, "member of the legion-linux group"):
            LegionServiceClient().request("feature.get", name="FnLockFeature")


class ServiceBackedModelTests(unittest.TestCase):
    def test_client_initialization_disables_local_hwmon_requirement(self):
        legion_path = Path(__file__).resolve().parents[1] / "legion_linux" / "legion.py"
        source = legion_path.read_text(encoding="utf-8")
        self.assertIn(
            "expect_hwmon=expect_hwmon and not use_legion_cli_to_write", source)

    def test_client_does_not_attempt_dmesg(self):
        legion_path = Path(__file__).resolve().parents[1] / "legion_linux" / "legion.py"
        source = legion_path.read_text(encoding="utf-8")
        self.assertIn("if not use_legion_cli_to_write:\n            log.info(get_dmesg())", source)


if __name__ == "__main__":
    unittest.main()
