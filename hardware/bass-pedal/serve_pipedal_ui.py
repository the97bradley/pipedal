#!/usr/bin/env python3
"""Serve a rebuilt PiPedal UI and reverse-proxy everything else to pipedald :80."""

from __future__ import annotations

import json
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = ("127.0.0.1", 80)
ROOT = Path.home() / "pipedal-ui"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args), flush=True)

    def _local_file(self) -> Path | None:
        path = self.path.split("?", 1)[0]
        local = Path(self.translate_path(path))
        if local.is_dir():
            index = local / "index.html"
            return index if index.is_file() else None
        return local if local.is_file() else None

    def _is_config_path(self) -> bool:
        path = self.path.split("?", 1)[0].rstrip("/")
        return path == "/var/config.json"

    def _upstream_config(self) -> dict:
        try:
            with socket.create_connection(UPSTREAM, timeout=10) as sock:
                sock.sendall(
                    b"GET /var/config.json HTTP/1.1\r\n"
                    b"Host: 127.0.0.1\r\n"
                    b"Connection: close\r\n\r\n"
                )
                raw = b""
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    raw += chunk
            body = raw.split(b"\r\n\r\n", 1)[1]
            data = json.loads(body)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {
            "socket_server_port": 80,
            "socket_server_address": "*",
            "ui_plugins": [],
            "max_upload_size": 536870912,
        }

    def serve_config(self) -> None:
        data = self._upstream_config()
        # Point the browser websocket at this preview origin so LAN/mDNS
        # clients do not follow pipedald's 127.0.0.1:80 from the proxy hop.
        data["socket_server_address"] = "*"
        data["socket_server_port"] = 5173
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.headers.get("Upgrade", "").lower() == "websocket":
            self.proxy_raw()
            return
        if self._is_config_path():
            self.serve_config()
            return
        if self._local_file() is not None:
            super().do_GET()
            return
        self.proxy_http()

    def do_HEAD(self) -> None:
        if self._local_file() is not None:
            super().do_HEAD()
            return
        self.proxy_http()

    def do_POST(self) -> None:
        self.proxy_http()

    def do_PUT(self) -> None:
        self.proxy_http()

    def do_DELETE(self) -> None:
        self.proxy_http()

    def proxy_http(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        request = self._format_request(body)
        try:
            with socket.create_connection(UPSTREAM, timeout=20) as sock:
                sock.sendall(request)
                sock.shutdown(socket.SHUT_WR)
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except OSError as exc:
            self.send_error(502, str(exc))

    def proxy_raw(self) -> None:
        request = self._format_request(b"")
        sock = socket.create_connection(UPSTREAM, timeout=20)
        sock.sendall(request)
        self.close_connection = True
        client = self.connection

        def pump(src: socket.socket, dst: socket.socket) -> None:
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

        threading.Thread(target=pump, args=(client, sock), daemon=True).start()
        pump(sock, client)
        try:
            sock.close()
        except OSError:
            pass

    def _format_request(self, body: bytes) -> bytes:
        path = self.path
        lines = [f"{self.command} {path} HTTP/1.1"]
        for key, value in self.headers.items():
            if key.lower() in ("connection", "keep-alive"):
                continue
            else:
                lines.append(f"{key}: {value}")
        if self.headers.get("Upgrade", "").lower() == "websocket":
            lines.append("Connection: Upgrade")
        else:
            lines.append("Connection: close")
        header = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")
        return header + body


def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"UI directory missing: {ROOT}")
    server = ThreadingHTTPServer(("0.0.0.0", 5173), Handler)
    print(
        f"PiPedal UI on http://0.0.0.0:5173  (files {ROOT}, api -> {UPSTREAM[0]}:{UPSTREAM[1]})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
