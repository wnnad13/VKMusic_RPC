"""
local_server.py

Локальный HTTP-сервер (только 127.0.0.1, снаружи недоступен), который
принимает обновления "сейчас играет" от браузерного расширения
(vkrpc-extension), работающего прямо в твоей открытой вкладке VK.

Это осознанная замена внешнему опросу vk.ru из Python: раз данные
теперь приходят из настоящей, уже залогиненной сессии браузера, для
антибот-системы VK это выглядит как обычный просмотр страницы, а не
как автоматизированный трафик.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED_ORIGINS = {"https://vk.ru", "https://vk.com"}


class TrackStore:
    """Потокобезопасное хранилище последнего полученного трека, с
    Event, чтобы основной цикл мог ждать новое обновление вместо
    постоянного опроса в холостую."""

    def __init__(self):
        self._lock = threading.Lock()
        self._track = None
        self._event = threading.Event()

    def set(self, track):
        with self._lock:
            self._track = track
        self._event.set()

    def wait_for_update(self, timeout=None):
        """Блокируется до нового обновления (или до истечения timeout),
        затем возвращает последний трек и сбрасывает флаг."""
        got_it = self._event.wait(timeout=timeout)
        if not got_it:
            return None
        with self._lock:
            track = self._track
        self._event.clear()
        return track


def make_handler(store: TrackStore):
    class Handler(BaseHTTPRequestHandler):
        def _cors_headers(self, origin):
            allowed = origin if origin in ALLOWED_ORIGINS else "https://vk.ru"
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors_headers(self.headers.get("Origin", ""))
            self.end_headers()

        def do_POST(self):
            origin = self.headers.get("Origin", "")
            if self.path != "/track":
                self.send_response(404)
                self._cors_headers(origin)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self._cors_headers(origin)
                self.end_headers()
                return
            store.set(data)
            self.send_response(204)
            self._cors_headers(origin)
            self.end_headers()

        def log_message(self, fmt, *args):
            pass  # тихий сервер, не спамим консоль HTTP-логами

    return Handler


def start_server(store: TrackStore, port=39285):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
