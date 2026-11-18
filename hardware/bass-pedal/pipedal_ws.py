#!/usr/bin/env python3
"""Minimal PiPedal websocket client (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import time


class PiPedalClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 80, path: str = "/pipedal"):
        self.host = host
        self.port = port
        self.path = path
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)
        self._buf = bytearray()
        self._next_id = 1
        self.client_id = -1
        self._handshake()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(req.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OSError("websocket handshake closed")
            data += chunk
        if b"101" not in data.split(b"\r\n", 1)[0]:
            raise OSError(f"websocket handshake failed: {data[:200]!r}")
        extra = data.split(b"\r\n\r\n", 1)[1]
        if extra:
            self._buf.extend(extra)

    def _mask_key(self) -> bytes:
        return os.urandom(4)

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        mask = self._mask_key()
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", n))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", n))
        header.extend(mask)
        self.sock.sendall(header + masked)

    def send_json(self, obj) -> None:
        self._send_frame(1, json.dumps(obj, separators=(",", ":")).encode())

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise OSError("socket closed")
            self._buf.extend(chunk)
        data = bytes(self._buf[:n])
        del self._buf[:n]
        return data

    def recv_message(self, timeout: float = 10.0) -> object | None:
        deadline = time.monotonic() + timeout
        payload = bytearray()
        op0 = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("websocket recv timeout")
            self.sock.settimeout(max(0.1, remaining))
            hdr = self._read_exact(2)
            fin = hdr[0] & 0x80
            opcode = hdr[0] & 0x0F
            masked = hdr[1] & 0x80
            length = hdr[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            data = self._read_exact(length)
            if masked:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x8:
                return None
            if opcode == 0x9:
                self._send_frame(0xA, data)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2) or opcode == 0x0:
                if op0 is None:
                    op0 = opcode
                payload.extend(data)
                if fin:
                    if op0 == 0x1:
                        return json.loads(payload.decode())
                    return bytes(payload)
            else:
                continue

    def request(self, message: str, body=None, timeout: float = 20.0):
        reply_to = self._next_id
        self._next_id += 1
        header = {"message": message, "replyTo": reply_to}
        self.send_json([header] if body is None else [header, body])
        deadline = time.monotonic() + timeout
        while True:
            msg = self.recv_message(timeout=max(0.1, deadline - time.monotonic()))
            if msg is None:
                raise OSError("server closed")
            if not isinstance(msg, list) or not msg:
                continue
            hdr = msg[0]
            if hdr.get("reply") == reply_to:
                if hdr.get("message") == "error":
                    raise RuntimeError(msg[1] if len(msg) > 1 else "error")
                return msg[1] if len(msg) > 1 else None

    def send(self, message: str, body=None) -> None:
        header = {"message": message}
        self.send_json([header] if body is None else [header, body])

    def hello(self) -> int:
        self.client_id = int(self.request("hello"))
        return self.client_id
