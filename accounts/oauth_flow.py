"""Browser sign-in helpers shared by Twitch and Google (OAuth "authorization code" flow)."""

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8766
REDIRECT = f"http://localhost:{PORT}/"  # must be registered with each app, exactly like this
DONE_PAGE = b"<html><body style='font-family:sans-serif'><h2>Signed in.</h2>You can close this tab.</body></html>"


def post_form(url, data):
    """POST form fields, return the JSON reply. Errors show the server's reason, never the inputs."""
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}: "
                           f"{e.read()[:200].decode('utf-8', 'replace')}") from None


def wait_for_code(auth_url, state, port=PORT, timeout=180, open_browser=True):
    """Open the sign-in page and wait for the redirect back to this computer. Returns the code."""
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            # Only the answer carrying our own state counts; stray requests can't cancel sign-in.
            if query.get("state") == [state] and ("code" in query or "error" in query):
                result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DONE_PAGE)

    class V6Server(HTTPServer):
        address_family = socket.AF_INET6

    # "localhost" can mean 127.0.0.1 or ::1 on Windows, so listen on both (this computer only).
    servers = [HTTPServer(("127.0.0.1", port), Handler)]
    try:
        servers.append(V6Server(("::1", port), Handler))
    except OSError:
        pass  # no IPv6 here; IPv4 is enough
    for srv in servers:
        srv.timeout = 0.5
    print("Opening your browser to sign in. If nothing opens, go to:")
    print("  " + auth_url)
    if open_browser:
        webbrowser.open(auth_url)
    deadline = time.time() + timeout
    try:
        while not result and time.time() < deadline:
            for srv in servers:
                srv.handle_request()
    finally:
        for srv in servers:
            srv.server_close()
    if not result:
        raise RuntimeError("Timed out waiting for sign-in (3 minutes).")
    if result.get("state") != state:
        raise RuntimeError("Sign-in answer did not match this request; try again.")
    if "error" in result:
        raise RuntimeError(f"Sign-in was refused: {result['error']}")
    return result["code"]
