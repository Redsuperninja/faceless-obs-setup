import _paths  # noqa: F401
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from accounts import tokens  # noqa: E402
tokens.PATH = Path(__file__).parent / 'no-such-tokens.json'  # never read real sign-ins in tests
from chat import chat_twitch  # noqa: E402
from accounts import env_loader  # noqa: E402
from chat import chat_youtube  # noqa: E402
import start_stream  # noqa: E402
from accounts import stream_push  # noqa: E402
from chat.chat_server import ChatBus, make_server  # noqa: E402


class TwitchParse(unittest.TestCase):
    LINE = ("@color=#FF4500;display-name=Cool\\sFan;id=abc :cool!cool@cool.tmi.twitch.tv "
            "PRIVMSG #chan :hi: there")

    def test_chat_line(self):
        m = chat_twitch.parse_privmsg(self.LINE)
        self.assertEqual((m["user"], m["color"], m["text"]), ("Cool Fan", "#FF4500", "hi: there"))

    def test_action_and_noise(self):
        m = chat_twitch.parse_privmsg(":a!a@a PRIVMSG #c :\x01ACTION waves\x01")
        self.assertEqual(m["text"], "waves")
        self.assertIsNone(chat_twitch.parse_privmsg(":tmi.twitch.tv 001 justinfan :Welcome"))

    def test_ping_gets_pong(self):
        sent = []
        chat_twitch.handle_line("PING :tmi.twitch.tv", lambda m: self.fail(), sent.append)
        self.assertEqual(sent, ["PONG :tmi.twitch.tv"])


class YouTubeBits(unittest.TestCase):
    def test_video_id(self):
        for t in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ",
                  "https://www.youtube.com/live/dQw4w9WgXcQ?feature=share", "dQw4w9WgXcQ"):
            self.assertEqual(chat_youtube.video_id_from(t), "dQw4w9WgXcQ")
        self.assertEqual(chat_youtube.video_id_from("nonsense"), "")

    def test_only_text_messages(self):
        base = {"id": "1", "authorDetails": {"displayName": "Ann"}}
        ok = {**base, "snippet": {"type": "textMessageEvent", "displayMessage": "yo"}}
        other = {**base, "snippet": {"type": "superChatEvent"}}
        self.assertEqual(chat_youtube.to_message(ok)["text"], "yo")
        self.assertIsNone(chat_youtube.to_message(other))


class ServerFeed(unittest.TestCase):
    def test_history_reaches_a_new_page(self):
        bus = ChatBus()
        bus.publish({"platform": "twitch", "user": "A", "color": "", "text": "first", "id": "1"})
        srv = make_server(bus, 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}"
            with urllib.request.urlopen(url + "/", timeout=5) as r:
                self.assertIn(b"EventSource", r.read())
            with urllib.request.urlopen(url + "/events", timeout=5) as r:
                line = r.readline().decode()
            self.assertEqual(json.loads(line[len("data: "):])["text"], "first")
        finally:
            srv.shutdown()
            srv.server_close()


class StreamInfo(unittest.TestCase):
    def test_enter_keeps_old_answer_and_newline_escape(self):
        answers = iter(["New title", "line1\\nline2", "", "", "", ""])
        out = start_stream.ask({"title": "Old", "category": "Keep me"}, lambda _p: next(answers))
        self.assertEqual(out["title"], "New title")
        self.assertEqual(out["description"], "line1\nline2")
        self.assertEqual(out["category"], "Keep me")

    def test_skipped_without_tokens(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIn("skipped", stream_push.push_twitch({"title": "t"}))
            self.assertIn("skipped", stream_push.push_youtube({"title": "t"}, "dQw4w9WgXcQ"))

    def test_youtube_sends_whole_snippet_with_trimmed_title(self):
        calls = []

        def fake(method, url, headers, body=None):
            calls.append((method, body))
            return {"items": [{"snippet": {"title": "old", "channelId": "c", "categoryId": "1"}}]}

        with mock.patch.dict("os.environ", {"YOUTUBE_ACCESS_TOKEN": "x"}), \
                mock.patch.object(stream_push, "_request", fake):
            stream_push.push_youtube({"title": "T" * 150, "description": "d", "youtube_category_id": "20"},
                                     "dQw4w9WgXcQ")
        method, body = calls[-1]
        self.assertEqual(method, "PUT")
        self.assertEqual(len(body["snippet"]["title"]), 100)
        self.assertEqual((body["snippet"]["categoryId"], body["snippet"]["channelId"]), ("20", "c"))

    def test_twitch_sets_title_and_category(self):
        calls = []

        def fake(method, url, headers, body=None):
            calls.append((method, body))
            if "search/categories" in url:
                return {"data": [{"id": "55", "name": "Just Chatting"}]}
            return {"data": [{"id": "me"}]}

        env = {"TWITCH_CLIENT_ID": "c", "TWITCH_ACCESS_TOKEN": "t"}
        with mock.patch.dict("os.environ", env), mock.patch.object(stream_push, "_request", fake):
            msg = stream_push.push_twitch({"title": "Hi", "category": "just chatting"})
        self.assertEqual(calls[-1], ("PATCH", {"title": "Hi", "game_id": "55"}))
        self.assertIn("Just Chatting", msg)


class EnvLoader(unittest.TestCase):
    def test_loads_values_but_real_env_wins_and_blanks_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text(chr(10).join(["# c", "A_KEY=one", "B_KEY='two'", "C_KEY=", "D_KEY=real_loses"]), encoding="utf-8")
            with mock.patch.dict(os.environ, {"D_KEY": "real"}, clear=False):
                env_loader.load_env(f)
                self.assertEqual((os.environ["A_KEY"], os.environ["B_KEY"], os.environ["D_KEY"]),
                                 ("one", "two", "real"))
                self.assertNotIn("C_KEY", os.environ)
                for k in ("A_KEY", "B_KEY"):
                    os.environ.pop(k, None)

    def test_missing_file_is_fine(self):
        env_loader.load_env(Path("does-not-exist.env"))


if __name__ == "__main__":
    unittest.main()
