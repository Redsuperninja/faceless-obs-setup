#!/usr/bin/env python3
"""
Sign in to Twitch and/or YouTube once, so start_stream.py can set your title and category.

    python get_tokens.py            # sign in to both
    python get_tokens.py twitch     # just one
    python get_tokens.py --check    # test the saved sign-ins (changes nothing)

Needs these in .env (see README): TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET,
YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET. Register this redirect address with both apps:
    http://localhost:8766/
Your browser opens, you approve, and a refresh token is saved to tokens.json (git-ignored).
After that the short-lived tokens renew themselves.
"""

import _root  # noqa: F401  (puts the project folder on the path)

import argparse
import base64
import hashlib
import os
import secrets
import urllib.parse

from accounts import stream_push
from accounts import tokens
from accounts.env_loader import load_env
from accounts.oauth_flow import REDIRECT, post_form, wait_for_code

load_env()
TWITCH_SCOPE = "channel:manage:broadcast moderator:read:followers"  # title/category + goal bar follower count
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"


def need(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise RuntimeError("Missing in .env: " + ", ".join(missing))
    return [os.environ[n] for n in names]


def twitch_auth_url(client_id, state):
    return "https://id.twitch.tv/oauth2/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": TWITCH_SCOPE, "state": state, "force_verify": "true"})


def youtube_auth_url(client_id, state, challenge):
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": YOUTUBE_SCOPE, "state": state, "access_type": "offline", "prompt": "consent",
        "code_challenge": challenge, "code_challenge_method": "S256"})


def sign_in_twitch():
    cid, secret = need("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)
    code = wait_for_code(twitch_auth_url(cid, state), state)
    tokens.save_tokens("twitch", post_form(tokens.SERVICES["twitch"]["token_url"], {
        "client_id": cid, "client_secret": secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": REDIRECT}))


def sign_in_youtube():
    cid, secret = need("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET")
    state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    code = wait_for_code(youtube_auth_url(cid, state, challenge), state)
    tokens.save_tokens("youtube", post_form(tokens.SERVICES["youtube"]["token_url"], {
        "client_id": cid, "client_secret": secret, "code": code, "code_verifier": verifier,
        "grant_type": "authorization_code", "redirect_uri": REDIRECT}))


def check():
    """Read-only test of both sign-ins."""
    try:
        tok = tokens.access_token("twitch")
        d = stream_push._request("GET", "https://id.twitch.tv/oauth2/validate",
                                 {"Authorization": f"OAuth {tok}"})
        scopes = d.get("scopes", [])
        missing = [x for x in TWITCH_SCOPE.split() if x not in scopes]
        print(f"Twitch: OK, signed in as {d['login']}" + (f" but missing permission: {', '.join(missing)} (run get_tokens.py twitch)" if missing else ""))
    except (RuntimeError, OSError, KeyError) as e:
        print(f"Twitch: not working ({e})")
    try:
        tok = tokens.access_token("youtube")
        d = stream_push._request("GET", "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 {"Authorization": f"Bearer {tok}"})
        items = d.get("items", [])
        print(f"YouTube: OK, channel {items[0]['snippet']['title']!r}" if items
              else "YouTube: token works but this Google account has no YouTube channel")
    except (RuntimeError, OSError, KeyError) as e:
        print(f"YouTube: not working ({e})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("service", nargs="?", choices=["twitch", "youtube", "all"], default="all")
    ap.add_argument("--check", action="store_true", help="test the saved sign-ins, change nothing")
    args = ap.parse_args()
    if args.check:
        return check()
    for name, fn in (("twitch", sign_in_twitch), ("youtube", sign_in_youtube)):
        if args.service in (name, "all"):
            try:
                fn()
                print(f"{name.capitalize()}: signed in and saved.")
            except RuntimeError as e:
                print(f"{name.capitalize()}: {e}")
    print("Run  python get_tokens.py --check  to test.")


if __name__ == "__main__":
    main()
