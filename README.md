# Faceless stream OBS setup

One script that builds a complete set of OBS scenes for a no-webcam channel, in either a 16:9 layout (Twitch and YouTube) or a 9:16 layout (TikTok). It talks to OBS through the WebSocket server that ships with OBS 28 and later, so there is nothing to import by hand.

The script creates its own **profile** and **scene collection** ("Faceless Twitch" or "Faceless TikTok Vertical"), so your current OBS setup is not touched. Running it again is safe: it only adds what is missing.

## What you get

| Scene | What's in it |
|---|---|
| Starting Soon | Background, big "STARTING SOON" title card, your tagline, plain right-hand column (goal bar and chat, no art panel), music |
| Starting Soon + Cam | The same with the framed art panel in the top right: the slot for an avatar or face cam later |
| Gameplay | Game Capture (Display Capture on Mac/Linux) framed 16:9 on the left; plain right-hand column (goal bar and chat, no art panel) |
| Display | The same with a Display Capture, for browsing, art, coding |
| Gameplay + Cam | Like Gameplay, but the right-hand column keeps the framed art panel: the slot for an avatar or face cam later |
| Display + Cam | Like Display, with the art panel |
| Just Chatting | Big chat on one side, the show title heading, goal bar, music (talk-only streams) |
| Chat Monitor | **Private.** Full-screen live Twitch chat for you to read. Don't switch to it while live |
| Be Right Back | Same look as Starting Soon with "BE RIGHT BACK" |
| Ending | "THANKS FOR WATCHING" plus a follow line for Twitch, YouTube and TikTok |

Two helper scenes, marked **[S]**, are nested inside the main ones: `[S] Background` and `[S] Alerts`. Change the alert URL once in `[S] Alerts` and every main scene picks it up. Chat is different: each scene gets its own `Chat (scene name)` box, sized exactly to its panel, because a nested scene would be shrunk and its text unreadable. They all load the same address, `overlays.chat_url` in `config.json`.

**Look and feel.** The style is ornate fantasy: double-line steel frames with flourished corners, orange gem diamonds, serif titles and dark gradient panels (inspired by `assets/image.png`). Your channel art (`media.background_file`, relative paths work) fills the background, darkened by `style.dim` (0 to 1, default 0.5). The frames are drawn by `web/frame.html` and a light glint slides along the metal. Chat sits in a framed panel with a LIVE CHAT tab, titles sit on framed cards over a moving rule, and a name plate shows your channel name and handle. Colors: `style.accent` is the light metal, `accent2` the gems and subtitles, `accent3` the dark metal shading; `style.font` is the title font (Georgia). There is no mascot right now. To add one, set `media.avatar_image` to a PNG (and optionally `media.avatar_crop` as `[left, top, right, bottom]` pixels to trim); it appears in a frame on each scene. Optional moving lines along the screen edges: `style.edge_lines` is `"none"` (default, cleanest), `"all"` (all four sides) or `"top_bottom"`. Everything decorative is named `Deco ...` in OBS. After changing any of this, rebuild with `--reset`. The frames only run while their scene is on screen, so they cost nothing otherwise.

In the vertical layout the gameplay sits in the top half with chat underneath, which is how most TikTok gaming streams are framed.

## Setup

1. **Install Python 3.9+**, then in this folder make a private environment and install the one dependency (PowerShell):
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
   Use `.venv\Scripts\python` instead of `python` for every command below (macOS/Linux: `.venv/bin/python`). Plain `python` may be a different Python that lacks the dependency, which shows as "Missing dependency".
2. **Turn on the OBS WebSocket server.** In OBS, open *Tools > WebSocket Server Settings*, tick *Enable WebSocket server*, and click *Show Connect Info* to copy the password. OBS shows a network address like `10.0.0.8` there; ignore it. The script runs on the same PC and uses `localhost`, port 4455 (set in `config.json`).
3. **Edit `config.json`.**
   - `channel`: your name, @handle, Twitch name and tagline (shown on the holding screens).
   - `style`: font, background color, accent color.
   - `overlays`: browser-source URLs for alerts, chat and an optional recent-events list (see below). Leave any of them empty and the source is created blank for you to fill in later.
   - `media`: optional paths to a background music file, a background image or video loop, and an avatar or mascot image (a PNGtuber or logo works well for a faceless channel).
4. **Run it** with OBS open:
   ```
   # Easiest: put OBS_WS_PASSWORD=your-password in a file named .env here, then:
   .venv\Scripts\python scripts/setup_obs.py

   # Or without .env (PowerShell)
   $env:OBS_WS_PASSWORD="your-password"; .venv\Scripts\python scripts/setup_obs.py
   ```
   For the TikTok layout, add `--layout vertical`.

### Options

| Flag | Does |
|---|---|
| `--target twitch` | With `--layout vertical`: the vertical profile streams to Twitch (uses `TWITCH_STREAM_KEY`) instead of TikTok |
| `--layout vertical` | Build the 9:16 TikTok version (1080x1920) in its own profile and collection |
| `--dry-run` | Print every request without connecting to OBS |
| `--reset` | Delete this script's scenes and sources first, then rebuild |
| `--no-profile` | Build into whatever profile and collection is open now, and leave video settings alone |

### Stream keys (optional)

Keys are read from environment variables or a local `.env` file (git-ignored), never from `config.json`, so the config is safe to share. `.env` uses simple `KEY=value` lines; real environment variables win over it. Every key the scripts read is listed below:

- `TWITCH_STREAM_KEY` sets Twitch as the stream destination on the horizontal profile.
- `TIKTOK_RTMP_URL` and `TIKTOK_STREAM_KEY` set a custom RTMP destination on the vertical profile.

You can also skip these and paste keys into *Settings > Stream* yourself.

## Seeing chat yourself

Viewers see chat through the bordered chat panel on each scene, but a faceless streamer also needs to read it. Set `channel.twitch_name` in `config.json`, then pick one:

- **Dock (best):** in OBS, *Docks > Custom Browser Docks*, add a dock named `Chat` with `https://www.twitch.tv/popout/YOURNAME/chat?popout=`. The script prints this link when it finishes. Log in inside the dock to chat back.
- **Second screen:** right-click the **Chat Monitor** scene, choose *Windowed Projector (Scene)* and move it to another monitor.

## Stream night: one chat box and one title

Run this each time you go live (after creating the YouTube stream in YouTube Studio so it has a link):

```
python scripts/start_stream.py
```

It asks for the **title, description and category** (Enter keeps your last answer, saved in `data/stream_info.json`), sets them on Twitch and YouTube, then starts the **combined chat box**. Use `--yes` to reuse the saved answers, `--dry-run` to see what would be sent without changing anything, and `--no-chat` to skip the chat box. For video, use **obs-multi-rtmp** or **Aitum Multistream** as described below; they only send the picture.

**Combined chat (like Restream).** `chat/chat_hub.py` reads Twitch and YouTube chat and shows both in one box at `http://localhost:8765/`. The setup script already points `Chat (browser)` and `Chat Monitor` at it, so viewers and you see the same box. Each line has a TW or YT badge. Run `python scripts/chat_hub.py --demo` to see fake messages while lining it up in OBS. Keep the window open while streaming.

- **Twitch chat** needs only `channel.twitch_name` in `config.json` (no login).
- **YouTube chat** needs `YOUTUBE_API_KEY` (Google Cloud Console > enable *YouTube Data API v3* > Credentials > API key). Each check costs a little of Google's free daily allowance (10,000 units), roughly 2 to 3 hours of chat a day, so it is for streaming sessions rather than leaving on all day.

**Setting title and category for you** needs a one-time sign-in:

1. Make an app on each platform and register this redirect address exactly: `http://localhost:8766/`
   - Twitch: dev.twitch.tv/console > Register Your Application (Client Type: Confidential).
   - Google: console.cloud.google.com > enable *YouTube Data API v3* > Credentials > OAuth client ID (Desktop app). Add yourself as a test user on the consent screen.
2. Put the IDs and secrets in `.env`: `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`.
3. Run `python scripts/get_tokens.py`. Your browser opens for each platform; approve it. A refresh token is saved to `%LOCALAPPDATA%/twitch-tools/tokens.json`, outside this folder so OneDrive and git never see it (set `TOKENS_FILE` to move it), and renews itself from then on.
4. `python scripts/get_tokens.py --check` tests both sign-ins without changing anything.

Without a sign-in that platform is skipped and the script says so; set it by hand in Twitch Stream Manager or YouTube Studio. (Pasting a short-lived `TWITCH_ACCESS_TOKEN` or `YOUTUBE_ACCESS_TOKEN` into `.env` still works as a fallback.) Google keeps apps in "testing" mode logged out after 7 days; if `--check` fails after a week, run `get_tokens.py youtube` again. Twitch has no description field, so only its title and category are set. Titles are cut at 140 (Twitch) and 100 (YouTube) characters.

## Layout and resizing

The right-hand column comes in two shared versions: `[S] Sidebar` (art panel with the show title, goal bar, chat) is used by **Starting Soon + Cam**, Be Right Back, **Gameplay + Cam** and **Display + Cam**; `[S] Sidebar Plain` (goal bar and a taller chat, no art panel) is used by the plain **Starting Soon**, **Gameplay** and **Display** scenes. The space to its left is the main area: the title card on the holding scenes, the 16:9 game or screen capture on Gameplay and Screen + Chat. Just Chatting keeps its own wide chat, and Ending has no sidebar.

Resize with a few numbers, then rebuild (`python scripts/setup_obs.py --reset`):

```
python scripts/layout.py show                          # current numbers, and the pixel size of each panel
python scripts/layout.py set sidebar_width 0.30        # wider right-hand column (the main area gives up the space)
python scripts/layout.py set goal_height 0.09
python scripts/layout.py set sidebar_height 0.45 --vertical
python scripts/layout.py reset
```

The numbers are `sidebar_width`, `margin`, `deco_height` (`auto` keeps the art panel 16:9), `goal_height` and `gap`; they live under `layout` in `config.json`. For a one-off nudge you can also drag things inside `[S] Sidebar` in OBS, but a rebuild puts them back.

**The art panel, and adding a face cam or avatar later.** The "+ Cam" scenes keep the framed panel in the top right as a slot. Change its text with `deco.title` in `config.json` (it shows the show title if you leave that blank), then rebuild with `--reset`. To put a face cam or avatar in it: in OBS open the scene `[S] Sidebar`, add a Video Capture Device (or an image) and drag it over the panel, above "Deco Sidebar Art". Everything that uses the panel (Be Right Back and the three "+ Cam" scenes) shows it. A `--reset` puts the panel back as built, so do the cam placement after your last rebuild (or ask me to add it to the builder). There is no cam or avatar by default; the plain Starting Soon, Gameplay and Display scenes never show the panel.

## Goal bar, commands, alerts, audio

**Goal bar.** Shows `data/goal.json` in the sidebar (and on Just Chatting). Its frame has no gem diamonds by default because they crowd a bar this short; set `goal_bar.gems` to `true` in `config.json` to bring them back, or `style.gems` to `false` to remove the diamonds from every frame (rebuild with `--reset` after). The socials bar (name and handle, bottom left) is plain too; `nameplate.gems` in `config.json` brings its diamonds back. `python -m chat.goal 42` sets the count; `--target`, `--label` change the rest. `python -m chat.goal --source twitch_followers` lets the chat box keep it up to date every minute, which needs one more permission: run `python scripts/get_tokens.py twitch` again (it now also asks for `moderator:read:followers`).

**Chat commands.** Typing `!guild`, `!socials`, `!rules`, `!music` or `!lurk` in either chat pops a framed card over the main area for about 9 seconds. Nothing is posted back to chat. Edit the cards, add commands, set `cooldown` seconds or `"mod_only": true` under `commands` in `config.json`. They only work while `chat/chat_hub.py` is running.

**Alerts.** The same chat box turns these into cards (7 seconds each, queued, centred over the main area): Twitch follows, subs, resubs, gift subs, raids and cheers (50 bits or more; change `alerts.min_bits`), and YouTube Super Chats and new members. Subs, raids and cheers come through chat and need no sign-in. **Follows** use Twitch's follow feed (EventSub) and need the one-time sign-in with the follower permission (`python scripts/get_tokens.py twitch`) and `TWITCH_CLIENT_ID` in `.env`; if that is missing the chat box says so once and carries on. `python scripts/chat_hub.py --demo` plays fake ones (and `!guild`) so you can see them.

**Alert sounds.** Each alert and command card plays a short sound from `assets/sounds/` (bells for follows and cheers, a harp run for subs, a fanfare for raids, and so on). I made them with `python scripts/make_sounds.py`, so there are no licenses to track; edit the notes in that file and rerun to change them. The sound comes out of the OBS source `Alerts (browser)`, so it has its own slider in the Audio Mixer: that is where you set the volume. Turn sounds off with `"alerts": {"sounds": false}` in `config.json`, or replace any `.wav` with your own of the same name.

**Audio.** The builder adds a shared `[S] Audio` scene with `Mic (Stream)` and `Desktop Audio (Stream)` (set 8 dB down), using your default Windows devices; pick your real microphone in OBS (right-click the source > Properties) and a rebuild will keep that choice and its level. If `BG Music` exists, it gets a "Duck Under Mic" filter so the music dips while you talk.

**Tune your voice to your mic.** The mic starts with a voice chain: Noise Suppression, Noise Gate, Gain, Compressor, Limiter. Those are only starting values. To fit them to your own voice and mic:

```
python scripts/mic_tune.py measure   # listens 25 s (quiet for 5 s, then talk normally) and prints your levels
python scripts/mic_tune.py apply     # same, then sets the filters from what it heard
python scripts/mic_tune.py check     # listens with the filters on: is the stream near the -17 dB target?
```

Re-run `apply` if you change microphone or move your mic. It bypasses the filters while it listens and always puts them back.

**If your voice sounds echoey:** check this before touching filters. If you listen on speakers (or OBS is set to monitor your sources out loud, the default for new sources), your mic hears the speakers and you get echo. Use headphones, or set the mic's Advanced Audio Properties (right-click the mixer > Advanced Audio Properties) Audio Monitoring to Monitor Off. In one test here this was the whole cause. OBS has no good software fix for a reverberant room: its AI echo removal (NVIDIA "dereverb") only works on NVIDIA graphics cards, so the real fixes are a closer mic, lower mic gain and soft furnishings.

**Text styles.** `fonts` in `config.json` picks a letter style for each part: `title` (`double_struck`), `chat` (`small_caps`), `alerts` (`fraktur`); `plain` turns it off.

**Stream tags.** `start_stream.py` asks for tags (comma separated) and sets them on Twitch (up to 10, letters and numbers only) and YouTube.

## Titles, music and YouTube Shorts

**Names on screen.** `channel.title` is the show name (shown as the Just Chatting heading) and `chat.title` is the tab text on every chat panel. Both are in `config.json`; the stream title you send to Twitch and YouTube comes from `start_stream.py` (its default is in `data/stream_info.example.json`). Fancy Unicode letters work on screen. In the stream title they look nice but are not searchable, and screen readers may read them letter by letter, so keep a plain-text version in the description or tags.

**Background music.** Put tracks in `assets/music/` (see the README there for sources and the license log) and rebuild with `--reset`. They play shuffled on the holding scenes and Just Chatting. The music is its own shared scene, `[S] Music`, so there is one slider for it: **`BG Music` in the OBS Audio Mixer**. It starts at -14 dB; set it there and a `--reset` keeps your level. It dips automatically while you talk. Audio files are git-ignored. This OBS has no VLC source, so playback uses `web/music.html`; `media.music_file` (one looping file) still works if the folder is empty.

**Vertical stream for YouTube (Shorts feed).** YouTube shows *vertical* live streams in the Shorts feed (on the phone app); its help says scheduled streams, Premieres and horizontal streams do not appear there, so use Go live now with a 9:16 picture. YouTube does not promise a stream will be shown. YouTube's own horizontal-plus-vertical mode is only rolling out to select creators, so the dependable route is a separate vertical stream.

Your OBS has the **Aitum Vertical** canvas (1080x1920). Build the vertical scenes straight into it:

```
.venv\Scripts\python scripts/setup_obs.py --layout vertical --canvas "Aitum Vertical" --reset
```

This only touches that canvas's scenes and the sources ending in "(V)"; your main (horizontal) scenes are never changed, and a main `--reset` leaves the vertical sources alone. Sources are shared by name in OBS, so vertical ones carry a "(V)" suffix. The vertical scenes use the main audio mix (no second mic), and their alert source is silent so sounds are not doubled. Use the Aitum Vertical dock to switch vertical scenes.

To send it to YouTube: in YouTube Studio choose Create > Go live and make a new stream with its **own stream key** for the vertical broadcast. In the Aitum Vertical dock settings add a custom RTMP output with YouTube's server address and that key (the exact menu names depend on your Aitum version; its docs are at aitum.tv/vertical). Twitch keeps getting the horizontal stream from the main canvas. Whether YouTube lets one channel run a horizontal and a vertical broadcast at the same time depends on your channel; if it does not, stream only the vertical one to YouTube. `layout.py set ... --vertical` resizes the vertical layout the same way as the horizontal one.

**Vertical stream for Twitch.** Twitch accepts a 9:16 stream too (it shows in the mobile app's vertical feed). Two ways:

- *Its own profile:* `TWITCH_STREAM_KEY=... python scripts/setup_obs.py --layout vertical --target twitch --reset`, then stream from the "Faceless TikTok Vertical" profile when you only want vertical on Twitch.
- *Both at once:* build the Aitum Vertical canvas as above, then in the Aitum Vertical dock add a Twitch output (Twitch's server and your stream key). Aitum outputs are set in its dock, not by this script. Twitch allows one live stream per channel, so use either the horizontal or the vertical one on Twitch at a time, unless your channel has Twitch's dual-format option.

**Bitrate.** Each layout has a `bitrate` (kbps) in `config.json`: 6000 horizontal, 4500 vertical. The builder writes it into the profile it makes (Simple output mode, 160 kbps audio). If the stream looks soft, raise it, rerun `setup_obs.py`, and keep it under about 70% of your upload speed (Twitch's limit is around 8000). Profiles you made by hand are not touched; set theirs in OBS under Settings > Output.

## Going live on Twitch and YouTube, and recording

**Default build.** `python scripts/setup_obs.py` (no flags) builds both layouts: the 16:9 scenes for Twitch and YouTube, then the 9:16 scenes into the Aitum Vertical canvas. If OBS has no such canvas it skips the vertical part and says so. Both run at 30 fps, which is steadier to watch and lighter on your CPU. The vertical scenes have no chat, because Twitch draws its own over a vertical stream. The game fills most of the screen (the centre of the picture, edges cropped), and your handle and the goal bar sit on its top edge, starting an eighth of the way down so Twitch's own overlays don't cover them (`python scripts/layout.py set top_offset 0.14 --vertical` moves them). The vertical scenes follow the main ones by name with no manual linking: `start_stream.py` starts `obs/scene_sync.py`, or run `python scripts/scene_sync.py` yourself while streaming. To read both chats inside OBS, close OBS and run `python scripts/chat_dock.py` once, then turn on *View > Docks > Chat (Twitch + YouTube)*; it fills while `start_stream.py` (or `chat/chat_hub.py`) is running. The horizontal chat has no header bar by default; put text in `chat.title` to bring one back.

**What you stream to today.** The "Faceless Twitch" profile sends to Twitch only (Twitch's Enhanced Broadcasting is on) at 6000 kbps. No multi-stream plugin is installed, so YouTube gets nothing yet. Your PC encodes on the CPU (x264); OBS found no NVIDIA encoder. It does list the AMD hardware encoder for your Radeon card, which would free the CPU if the stream stutters.

**Twitch and YouTube at once.** Install the Aitum Multistream plugin (or Aitum Stream Suite, which includes it) and add a YouTube output with its stream key. It reuses the one encode, so it costs upload bandwidth (about 6000 kbps per site) but little extra CPU. A vertical output is added in the Aitum Vertical settings.

**Recording for videos.** The OBS Record button saves the main picture to your Videos folder (hybrid MP4, which survives a crash). Aitum Vertical records the vertical picture separately. Record every stream locally: it is the only copy you control.

**Twitch or YouTube VODs.** Both keep a copy you can download later. Twitch: turn on *Settings > Stream > Store past broadcasts*, then *Creator Dashboard > Content > Video Producer > Download*. Twitch deletes them after a limited time (about 14 days for most channels, longer for Partners; check your own), so download soon. YouTube keeps the stream as a video until you delete it: *YouTube Studio > Content > Live*, then Download. Quality is lower than your local recording, so treat these as a backup.

## Alerts and chat overlays

Any browser-source overlay service works. The common free ones:

- **StreamElements** (streamelements.com): *Streaming tools > Overlays*, add an *AlertBox* widget and a *Chat* widget, then copy each overlay's URL.
- **Streamlabs** (streamlabs.com): *Alert Box* and *Chat Box* each give you a widget URL.

Paste the alert URL into `overlays.alerts_url` and the chat URL into `overlays.chat_url`, then rerun the script, or paste them straight into the `Alerts (browser)` and `Chat (browser)` sources in OBS. These URLs contain a private token, so don't post them anywhere.

## Streaming to YouTube and TikTok at the same time

Twitch has allowed simulcasting to other platforms since late 2023. There are two ways to do it.

### Option A: free, from your own PC

This needs more upload bandwidth, roughly the bitrate of each stream added together (for example 6000 + 6000 + 3000 kbps).

- **YouTube (16:9):** install the **Aitum Multistream** plugin, or the older **obs-multi-rtmp** plugin. Add a YouTube output with the stream key from *YouTube Studio > Create > Go live > Stream*. If you've never streamed on YouTube, the channel needs live streaming enabled first, and that can take up to 24 hours. The YouTube output sends the same 16:9 scenes Twitch gets.
- **TikTok (9:16):** install the **Aitum Vertical** plugin. It adds a second, vertical canvas inside the same OBS, with its own scenes and its own stream output, so you can go live on Twitch, YouTube and TikTok from one OBS at once. Rebuild the vertical scenes there using the `--layout vertical` collection as a reference, or nest your horizontal scenes inside it.
  - TikTok only gives out an RTMP server URL and stream key to accounts with LIVE access (age and follower requirements apply and change over time). If you have access, the key is under *LIVE Center / LIVE Producer* on tiktok.com. It may change every time you go live, so check it before each stream.

If you only stream to TikTok sometimes, you can skip Aitum Vertical. Switch OBS to the *Faceless TikTok Vertical* profile and collection that this script made, and stream to TikTok on its own.

### Option B: a relay service

**Restream.io** (or a similar service) takes one stream from OBS and forwards it to Twitch, YouTube and TikTok, so your upload only carries one stream. The free tier has limits, and a single feed means TikTok gets your 16:9 picture letterboxed rather than a true vertical layout.

## Tips for a faceless channel

- Add your mic and desktop audio under *Settings > Audio*. Those are global, so the script doesn't create them. If you talk, a mic noise suppression filter helps a lot.
- An avatar, PNGtuber or VTuber model in the corner keeps the stream personal without a camera. Point `media.avatar_image` at a PNG or a looping video.
- Set hotkeys for scene switching under *Settings > Hotkeys*, or use a Stream Deck.
- On macOS and Linux there is no Game Capture, so the Gameplay scene uses Display Capture instead. Swap it for a window capture in OBS if you want just the game window.

## Files

Run things from `scripts/` (for example `python scripts/start_stream.py`); the code they use lives in the folders below.

| Folder | What's in it |
|---|---|
| `scripts/` | The commands you run: `setup_obs.py` (scene builder), `start_stream.py`, `chat_hub.py`, `get_tokens.py`, `layout.py`, `scene_sync.py`, `mic_tune.py`, `make_sounds.py`, `youtube_streams.py`, `chat_dock.py`, and the **Stream Launcher** (`launcher.py`; run `.\scriptsbuild_launcher.ps1` once to make `Stream Launcher.exe` in the project folder, keep it there) |
| `obs/` | Scene-building parts: `layout`, `sidebar`, `flair` (borders, plate, mascot), `extra_scenes`, `names`, `textstyle`, `audio`, `music`, `output` (bitrate), `canvas` (Aitum Vertical), `scene_sync` |
| `chat/` | The combined chat box and its extras: `chat_hub`, `chat_server`, `chat_twitch`, `chat_youtube`, `commands`, `alerts`, `goal`, `eventsub` (Twitch follows) |
| `accounts/` | `env_loader` (reads `.env`), `tokens` and `oauth_flow` (sign-in and renewal; tokens are saved outside the project), `stream_push` (sets stream info on Twitch and YouTube) |
| `web/` | Pages shown in OBS: `chat.html`, `overlay.html`, `goal.html`, `frame.html`, `music.html` |
| `data/` | Your saved answers: `stream_info.json` and `goal.json` (git ignores them), plus the `.example.json` starting copies |
| `assets/` | Channel art, logos, alert sounds, music |
| `tests/` | `python -m unittest discover -s tests` |

In the project folder: `config.json` (your channel details, colors, overlay URLs and media paths), `requirements.txt`, `LICENSE` (MIT) and, once you build it, `Stream Launcher.exe`.
