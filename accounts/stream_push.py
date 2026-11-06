"""Set the stream title, description and category on Twitch and YouTube.

Tokens come from tokens.py (saved by get_tokens.py), or these environment variables:
    TWITCH_CLIENT_ID, TWITCH_ACCESS_TOKEN   (token scope: channel:manage:broadcast)
    YOUTUBE_ACCESS_TOKEN                    (OAuth token, scope: youtube)
Twitch has no description field, so only its title and category are set.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from accounts import tokens

TWITCH_MAX_TITLE = 140
YOUTUBE_MAX_TITLE = 100


def parse_tags(text):
    """'fantasy, roguelike ,Faceless' -> ['fantasy', 'roguelike', 'Faceless'] (also accepts a list)."""
    items = text if isinstance(text, list) else str(text or "").split(",")
    return [t.strip() for t in items if t.strip()]


def twitch_tags(tags):
    """Twitch tags: letters and numbers only, at most 25 characters each, at most 10 in all."""
    out, seen = [], set()
    for tag in tags:
        clean = re.sub(r"[^A-Za-z0-9]", "", tag)[:25]
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out[:10]


def youtube_tags(tags, limit=450):
    """YouTube tags: keep as typed, but stay inside its total length limit (500, with quoting)."""
    out, used = [], 0
    for tag in tags:
        used += len(tag) + 3
        if used > limit:
            break
        out.append(tag)
    return out


def _request(method, url, headers, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        # Never include the headers: they hold the access token.
        raise RuntimeError(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}: "
                           f"{e.read()[:200].decode('utf-8', 'replace')}") from None


def push_twitch(info):
    cid, token = os.environ.get("TWITCH_CLIENT_ID"), tokens.access_token("twitch")
    if not (cid and token):
        return "skipped (run get_tokens.py, or set TWITCH_CLIENT_ID and TWITCH_ACCESS_TOKEN)"
    h = {"Client-Id": cid, "Authorization": f"Bearer {token}"}
    me = _request("GET", "https://api.twitch.tv/helix/users", h)["data"][0]["id"]
    body = {"title": info["title"][:TWITCH_MAX_TITLE]}
    note = ""
    tags = twitch_tags(parse_tags(info.get("tags")))
    if tags:
        body["tags"] = tags
        note = f", {len(tags)} tags"
    if info.get("category"):
        q = urllib.parse.urlencode({"query": info["category"], "first": 1})
        found = _request("GET", f"https://api.twitch.tv/helix/search/categories?{q}", h)["data"]
        if found:
            body["game_id"] = found[0]["id"]
            note += f", category '{found[0]['name']}'"
        else:
            note += f", NO category match for '{info['category']}' (title still set)"
    _request("PATCH", f"https://api.twitch.tv/helix/channels?broadcaster_id={me}", h, body)
    return f"updated title{note}"


def push_youtube(info, video_id):
    if not video_id:
        return "skipped (no YouTube video given)"
    token = tokens.access_token("youtube")
    if not token:
        return "skipped (run get_tokens.py, or set YOUTUBE_ACCESS_TOKEN)"
    h = {"Authorization": f"Bearer {token}"}
    base = "https://www.googleapis.com/youtube/v3/videos"
    items = _request("GET", f"{base}?part=snippet&id={video_id}", h).get("items", [])
    if not items:
        return "failed: video not found (or the token belongs to a different channel)"
    snippet = items[0]["snippet"]  # update needs the whole snippet back, so edit a copy
    snippet["title"] = info["title"][:YOUTUBE_MAX_TITLE]
    snippet["description"] = info.get("description", "")
    tags = youtube_tags(parse_tags(info.get("tags")))
    if tags:
        snippet["tags"] = tags
    if info.get("youtube_category_id"):
        snippet["categoryId"] = str(info["youtube_category_id"])
    _request("PUT", f"{base}?part=snippet", h, {"id": video_id, "snippet": snippet})
    return "updated title, description, category" + (f" and {len(tags)} tags" if tags else "")
