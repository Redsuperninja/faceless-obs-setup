import _paths  # noqa: F401
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chat import alerts  # noqa: E402
from chat import chat_twitch  # noqa: E402
from chat import chat_youtube  # noqa: E402
from chat import goal  # noqa: E402
from accounts import stream_push  # noqa: E402
from obs import textstyle  # noqa: E402
from chat.chat_hub import make_publish  # noqa: E402
from chat.chat_server import ChatBus  # noqa: E402
from chat.commands import Commands  # noqa: E402

CFG = {"fonts": {"title": "double_struck", "chat": "small_caps", "alerts": "fraktur"},
       "commands": {"guild": {"title": "Welcome", "text": "hi", "cooldown": 30},
                    "mods": {"title": "Mods", "text": "only", "mod_only": True}}}


class TextStyles(unittest.TestCase):
    def test_double_struck_uses_the_special_letters_and_keeps_the_rest(self):
        self.assertEqual(textstyle.double_struck("FANTASY QUEST"), "𝔽𝔸ℕ𝕋𝔸𝕊𝕐 ℚ𝕌𝔼𝕊𝕋")
        self.assertEqual(textstyle.double_struck("a1!"), "𝕒𝟙!")

    def test_small_caps_and_fraktur(self):
        self.assertEqual(textstyle.small_caps("Welcome to the guild"), "ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ɢᴜɪʟᴅ")
        self.assertEqual(textstyle.fraktur("Raid"), "ℜ𝔞𝔦𝔡")
        self.assertEqual(textstyle.apply_style("nonsense", "Plain"), "Plain")
        self.assertEqual(textstyle.font_for(CFG, "chat"), "small_caps")


class Events(unittest.TestCase):
    def test_twitch_raid_sub_and_cheer(self):
        raid = chat_twitch.parse_alert("@msg-id=raid;msg-param-displayName=Wanderer;msg-param-viewerCount=12 "
                                       ":tmi.twitch.tv USERNOTICE #c")
        self.assertEqual((raid["kind"], raid["user"], raid["detail"]), ("raid", "Wanderer", "12"))
        sub = chat_twitch.parse_alert("@msg-id=resub;display-name=Ann;msg-param-cumulative-months=7 "
                                      ":tmi.twitch.tv USERNOTICE #c")
        self.assertEqual((sub["kind"], sub["detail"]), ("resub", "7"))
        cheer = chat_twitch.parse_alert("@bits=100;display-name=Bo :bo!bo@bo PRIVMSG #c :cheer100 hi")
        self.assertEqual((cheer["kind"], cheer["detail"]), ("bits", "100"))
        self.assertIsNone(chat_twitch.parse_alert("@display-name=Bo :bo!bo@bo PRIVMSG #c :hello"))

    def test_mod_badge(self):
        m = chat_twitch.parse_privmsg("@badges=moderator/1;display-name=M :m!m@m PRIVMSG #c :!x")
        self.assertTrue(m["mod"])

    def test_youtube_superchat_and_member(self):
        item = {"id": "1", "authorDetails": {"displayName": "Fan"},
                "snippet": {"type": "superChatEvent",
                            "superChatDetails": {"amountDisplayString": "$5.00", "userComment": "yo"}}}
        a = chat_youtube.to_alert(item)
        self.assertEqual((a["kind"], a["detail"], a["comment"]), ("superchat", "$5.00", "yo"))
        self.assertIsNone(chat_youtube.to_message(item))
        item["snippet"] = {"type": "newSponsorEvent"}
        self.assertEqual(chat_youtube.to_alert(item)["kind"], "member")

    def test_alert_gets_fraktur_title_and_sentence(self):
        out = alerts.decorate({"type": "alert", "kind": "raid", "user": "W", "detail": "12"}, CFG)
        self.assertEqual(out["title"], textstyle.fraktur("Raid!"))
        self.assertEqual(out["text"], "W arrives with 12 raiders")


class ChatCommands(unittest.TestCase):
    def test_command_cooldown_and_mod_only(self):
        t = [0.0]
        cmds = Commands(CFG["commands"], clock=lambda: t[0])
        say = lambda text, mod=False: cmds.handle({"user": "u", "text": text, "mod": mod})  # noqa: E731
        self.assertEqual(say("!guild")["text"], "hi")
        self.assertIsNone(say("!guild"))          # cooling down
        t[0] = 31
        self.assertIsNotNone(say("!GUILD now"))   # case-insensitive, extra words fine
        self.assertIsNone(say("!mods"))           # not a mod
        t[0] = 45                                 # past the 10s gap between any two command cards
        self.assertIsNotNone(say("!mods", mod=True))
        self.assertIsNone(say("hello !guild"))    # must start with !
        self.assertIsNone(cmds.handle({"type": "alert", "text": "!guild"}))

    def test_publish_turns_a_command_into_a_styled_card(self):
        bus = ChatBus()
        make_publish(bus, CFG)({"platform": "twitch", "user": "u", "text": "!guild", "mod": False})
        types = [m.get("type") for m in bus.history]
        self.assertEqual(types, [None, "command"])
        self.assertEqual(bus.history[1]["title"], textstyle.small_caps("Welcome"))


class Goal(unittest.TestCase):
    def test_read_write_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "goal.json"
            self.assertEqual(goal.read(p)["target"], 100)  # missing file -> defaults
            goal.write({"label": "L", "current": 5, "target": 10, "source": "manual"}, p)
            self.assertEqual(goal.read(p)["current"], 5)
            p.write_text("not json", encoding="utf-8")
            self.assertEqual(goal.read(p)["current"], 0)


class Tags(unittest.TestCase):
    def test_twitch_tags_are_cleaned_and_capped(self):
        tags = stream_push.parse_tags("Fantasy, roguelike , Faceless!, fantasy, " + ", ".join(f"t{i}" for i in range(20)))
        out = stream_push.twitch_tags(tags)
        self.assertEqual(out[:3], ["Fantasy", "roguelike", "Faceless"])
        self.assertEqual(len(out), 10)

    def test_youtube_tags_stay_inside_the_length_limit(self):
        out = stream_push.youtube_tags(["x" * 200, "y" * 200, "z" * 100])
        self.assertEqual(len(out), 2)


class Protections(unittest.TestCase):
    def test_global_command_cooldown(self):
        t = [0.0]
        cmds = Commands({"a": {"title": "A", "text": "x", "cooldown": 1}, "b": {"title": "B", "text": "y", "cooldown": 1}},
                        clock=lambda: t[0])
        self.assertIsNotNone(cmds.handle({"user": "u", "text": "!a"}))
        t[0] = 5
        self.assertIsNone(cmds.handle({"user": "u", "text": "!b"}))   # another command too soon
        t[0] = 11
        self.assertIsNotNone(cmds.handle({"user": "u", "text": "!b"}))

    def test_gift_bomb_recipients_and_small_cheers_are_skipped(self):
        one = chat_twitch.parse_alert("@msg-id=subgift;display-name=G;msg-param-community-gift-id=123 "
                                      ":tmi.twitch.tv USERNOTICE #c")
        self.assertIsNone(one)
        bus = ChatBus()
        pub = make_publish(bus, {"alerts": {"min_bits": 50}})
        pub({"type": "alert", "kind": "bits", "user": "x", "detail": "1"})
        pub({"type": "alert", "kind": "bits", "user": "x", "detail": "100"})
        self.assertEqual(len(bus.history), 1)

    def test_server_only_answers_requests_addressed_to_this_computer(self):
        from chat.chat_server import make_server
        srv = make_server(ChatBus(), 0)
        port = srv.server_address[1]
        srv.RequestHandlerClass = type(srv.RequestHandlerClass)  # noqa: keep the class; rebuild below with the port
        from chat.chat_server import make_handler
        srv.RequestHandlerClass = make_handler(ChatBus(), {"/goal.json": lambda: {"ok": 1}}, port)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            def get(host):
                req = urllib.request.Request(f"http://127.0.0.1:{port}/goal.json", headers={"Host": host})
                return urllib.request.urlopen(req, timeout=5).status
            self.assertEqual(get(f"localhost:{port}"), 200)
            self.assertEqual(get(f"127.0.0.1:{port}"), 200)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                get("evil.example.com")
            self.assertEqual(cm.exception.code, 403)
        finally:
            srv.shutdown()
            srv.server_close()


class AlertSounds(unittest.TestCase):
    def test_every_alert_kind_and_commands_have_a_sound_file(self):
        for kind in list(alerts.ALERTS) + ["command"]:
            self.assertTrue((alerts.SOUNDS / f"{kind}.wav").exists(), kind)

    def test_decorate_names_the_sound_and_sounds_can_be_switched_off(self):
        ev = {"type": "alert", "kind": "follow", "user": "F"}
        self.assertEqual(alerts.decorate(ev, CFG)["sound"], "follow.wav")
        self.assertIsNone(alerts.decorate(ev, {**CFG, "alerts": {"sounds": False}})["sound"])
        cmd = alerts.decorate({"type": "command", "title": "T", "text": "x"}, CFG)
        self.assertEqual(cmd["sound"], "command.wav")

    def test_sounds_are_real_audio_not_silent_or_clipped(self):
        import wave
        for f in alerts.SOUNDS.glob("*.wav"):
            with wave.open(str(f)) as w:
                data = w.readframes(w.getnframes())
            import array
            samples = array.array("h", data)
            peak = max(abs(x) for x in samples)
            self.assertGreater(peak, 8000, f.name)      # audible
            self.assertLess(peak, 32767, f.name)        # not clipped
            self.assertLess(len(samples) / 44100, 2.6, f.name)  # short

    def test_server_serves_sounds_and_refuses_anything_else(self):
        from chat.chat_server import make_handler, make_server
        srv = make_server(ChatBus(), 0)
        port = srv.server_address[1]
        srv.RequestHandlerClass = make_handler(ChatBus(), {}, port)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            def code(path):
                try:
                    return urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=5).status
                except urllib.error.HTTPError as e:
                    return e.code
            self.assertEqual(code("/sounds/follow.wav"), 200)
            self.assertEqual(code("/sounds/..%2Fconfig.json"), 404)
            self.assertEqual(code("/sounds/nope.wav"), 404)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
