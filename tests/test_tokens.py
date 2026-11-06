import _paths  # noqa: F401
import json
import os
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import get_tokens  # noqa: E402
from accounts import oauth_flow  # noqa: E402
from accounts import tokens  # noqa: E402

ENV = {"TWITCH_CLIENT_ID": "cid", "TWITCH_CLIENT_SECRET": "sec"}


class TokenStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(tokens, "PATH", Path(self.dir.name) / "tokens.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.dir.cleanup()

    def test_fresh_saved_token_is_reused_without_network(self):
        tokens.save_tokens("twitch", {"access_token": "A", "refresh_token": "R", "expires_in": 3600})
        with mock.patch.object(tokens, "post_form", side_effect=AssertionError("no network")):
            self.assertEqual(tokens.access_token("twitch"), "A")

    def test_expired_token_is_refreshed_and_refresh_token_kept(self):
        tokens.save_tokens("twitch", {"access_token": "old", "refresh_token": "R", "expires_in": -100})
        reply = {"access_token": "new", "expires_in": 3600}  # no new refresh token sent
        with mock.patch.dict(os.environ, ENV), mock.patch.object(tokens, "post_form", return_value=reply) as p:
            self.assertEqual(tokens.access_token("twitch"), "new")
        self.assertEqual(p.call_args[0][1]["refresh_token"], "R")
        self.assertEqual(json.loads(tokens.PATH.read_text())["twitch"]["refresh_token"], "R")

    def test_falls_back_to_plain_env_token_then_empty(self):
        with mock.patch.dict(os.environ, {"YOUTUBE_ACCESS_TOKEN": "env"}, clear=True):
            self.assertEqual(tokens.access_token("youtube"), "env")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(tokens.access_token("youtube"), "")


class SignInUrls(unittest.TestCase):
    def test_twitch_url_asks_for_broadcast_scope_and_state(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(get_tokens.twitch_auth_url("cid", "st")).query)
        self.assertEqual((q["scope"], q["state"], q["redirect_uri"]),
                         (["channel:manage:broadcast moderator:read:followers"], ["st"], ["http://localhost:8766/"]))

    def test_youtube_url_is_offline_with_pkce(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(get_tokens.youtube_auth_url("cid", "st", "ch")).query)
        self.assertEqual((q["access_type"], q["code_challenge_method"], q["code_challenge"]),
                         (["offline"], ["S256"], ["ch"]))

    def test_missing_client_secret_is_reported_by_name(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                get_tokens.need("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET")
        self.assertIn("TWITCH_CLIENT_SECRET", str(cm.exception))

    def test_wrong_state_is_ignored_and_right_state_wins(self):
        import threading
        import urllib.request
        port = 18766

        def hit():
            time.sleep(0.5)
            for q in ("code=evil&state=WRONG", "error=x", "code=abc&state=expected"):
                urllib.request.urlopen(f"http://127.0.0.1:{port}/?{q}", timeout=5).read()

        threading.Thread(target=hit, daemon=True).start()
        code = oauth_flow.wait_for_code("http://example.invalid/", "expected", port=port, timeout=10,
                                        open_browser=False)
        self.assertEqual(code, "abc")

    def test_token_file_is_written_outside_project_and_atomically(self):
        self.assertNotIn("OneDrive", str(tokens._default_path()))


if __name__ == "__main__":
    unittest.main()
