"""Read YouTube live chat with the official Data API (needs YOUTUBE_API_KEY)."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3"
MIN_POLL_SECONDS = 5  # each poll costs 5 of the 10,000 free daily quota units


def video_id_from(text):
    """Accept a full YouTube link (watch, live, youtu.be) or a bare 11-character id."""
    text = text.strip()
    m = re.search(r"(?:v=|youtu\.be/|/live/|/embed/)([\w-]{11})", text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"[\w-]{11}", text) else ""


def get_json(path, params):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # The URL holds the key, so never echo it; show only Google's reason.
        raise RuntimeError(f"YouTube API {e.code}: {e.read()[:200].decode('utf-8', 'replace')}") from None


def live_chat_id(key, video_id):
    data = get_json("videos", {"part": "liveStreamingDetails", "id": video_id, "key": key})
    items = data.get("items", [])
    chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId") if items else None
    if not chat_id:
        raise RuntimeError("That video has no active live chat (is the stream live yet?)")
    return chat_id


def to_message(item):
    if item["snippet"].get("type") != "textMessageEvent":
        return None  # super chats and memberships are handled by to_alert
    who = item["authorDetails"]
    return {"platform": "youtube", "user": who["displayName"], "color": "",
            "text": item["snippet"].get("displayMessage", ""), "id": item["id"],
            "mod": bool(who.get("isChatModerator") or who.get("isChatOwner"))}


def to_alert(item):
    """Super Chats and new members as alert events (None for everything else)."""
    snippet, user = item["snippet"], item["authorDetails"]["displayName"]
    if snippet.get("type") == "superChatEvent":
        d = snippet.get("superChatDetails", {})
        return {"type": "alert", "kind": "superchat", "user": user, "platform": "youtube",
                "detail": d.get("amountDisplayString", ""), "comment": d.get("userComment", "")}
    if snippet.get("type") == "newSponsorEvent":
        return {"type": "alert", "kind": "member", "user": user, "platform": "youtube", "detail": ""}
    return None


def run(key, video_id, publish, stop, log=print):
    token, first = "", True
    chat_id = None
    while not stop.is_set():
        wait = 10
        try:
            chat_id = chat_id or live_chat_id(key, video_id)
            params = {"liveChatId": chat_id, "part": "snippet,authorDetails", "key": key}
            if token:
                params["pageToken"] = token
            data = get_json("liveChat/messages", params)
            token = data.get("nextPageToken", token)
            if first:
                log("YouTube chat: connected")
            else:  # the first batch is old history; don't replay it
                for item in data.get("items", []):
                    msg = to_message(item) or to_alert(item)
                    if msg:
                        publish(msg)
            first = False
            wait = max(MIN_POLL_SECONDS, data.get("pollingIntervalMillis", 5000) / 1000)
        except (RuntimeError, OSError) as e:
            log(f"YouTube chat: {e}; retrying in {wait}s")
        stop.wait(wait)
