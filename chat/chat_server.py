"""Tiny local web server: a page for OBS plus a live feed (server-sent events)."""

import json
import queue
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
# Fixed list of pages the server will hand out (nothing else on disk is reachable).
SOUNDS = HERE / "assets" / "sounds"
LOGOS = HERE / "assets" / "logos"
PAGES = {"/": "chat.html", "/overlay": "overlay.html", "/goal": "goal.html", "/frame.html": "frame.html"}


class ChatBus:
    """Keeps the last few messages and hands new ones to every open page."""

    def __init__(self, keep=100):
        self.keep = keep
        self.history = []
        self.subs = []
        self.lock = threading.Lock()

    def publish(self, msg):
        with self.lock:
            self.history.append(msg)
            del self.history[:-self.keep]
            subs = list(self.subs)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass  # a stuck page must not slow the others down

    def subscribe(self):
        q = queue.Queue(maxsize=500)
        with self.lock:
            self.subs.append(q)
            return q, list(self.history)

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)


def make_handler(bus, data=None, port=None):
    data = data or {}  # path -> function returning JSON, e.g. {"/goal.json": read_goal}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console for chat status
            pass

        def do_GET(self):
            if port and self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send_error(403)  # a web page on another name pointing here (DNS rebinding)
                return
            path, _, query = self.path.partition("?")
            if path in PAGES:
                self.send_body("text/html; charset=utf-8", (HERE / "web" / PAGES[path]).read_bytes())
            elif path.startswith("/sounds/"):
                name = urllib.parse.unquote(path[len("/sounds/"):])
                if name in {p.name for p in SOUNDS.glob("*.wav")}:  # only files that really are in that folder
                    self.send_body("audio/wav", (SOUNDS / name).read_bytes())
                else:
                    self.send_error(404)
            elif path.startswith("/logos/") and path[len("/logos/"):] in {p.name for p in LOGOS.glob("*.svg")}:
                self.send_body("image/svg+xml", (LOGOS / path[len("/logos/"):]).read_bytes())
            elif path in data:
                self.send_body("application/json; charset=utf-8", json.dumps(data[path]()).encode())
            elif path == "/events":
                self.stream_events(live_only="live=1" in query)
            else:
                self.send_error(404)

        def send_body(self, content_type, body):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def stream_events(self, live_only=False):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            q, history = bus.subscribe()
            try:
                for msg in ([] if live_only else history):  # overlays must not replay old alerts
                    self.wfile.write(f"data: {json.dumps(msg)}\n\n".encode())
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(msg)}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")  # keeps the connection open
                    self.wfile.flush()
            except OSError:  # page closed (broken pipe / connection reset)
                pass
            finally:
                bus.unsubscribe(q)

    return Handler


def make_server(bus, port, data=None):
    """Only listens on this computer (127.0.0.1); OBS runs here too."""
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(bus, data, port))
    srv.daemon_threads = True
    return srv
