# Background music

Drop `.mp3`, `.ogg`, `.wav`, `.m4a`, `.flac` or `.opus` files in this folder. The scene builder plays all of them
shuffled on a loop on Starting Soon, Be Right Back, Ending and Just Chatting (and stops when you leave those
scenes). Volume is `media.music_volume` in `config.json` (0 to 1). Rebuild with `--reset` after adding tracks.

The audio files are git-ignored (big, and not ours to republish). This file is the only thing committed here.

## Where to get tracks

- **Pixabay Music** (https://pixabay.com/music/): free, no sign-in needed to listen, a free account to download.
  Pixabay's license summary says content can be used for free without attribution, but not sold or redistributed
  on its own. Its summary does not mention YouTube Content ID, so a claim on a track is still possible: if a track
  gets claimed, drop it.
  - Fantasy: https://pixabay.com/music/search/fantasy/
  - Technomodern: try searches like `synthwave ambient`, `cyberpunk ambient`, `sci-fi fantasy`, `cinematic electronic`.
- **OpenGameArt** (https://opengameart.org/): many CC0 tracks (no attribution needed). Check the license shown on each
  track's own page; some packs are CC-BY or CC-BY-SA, which do need credit.

## Keep a record (do this for every track)

Streaming music you can't prove a license for is how channels get muted or struck. Add a line per track:

| File | Title | Artist | Source page | License as shown | Flags on the page | Checked |
|---|---|---|---|---|---|---|
| `held/alex-morgan-fantasy-adventure-quest-537478.mp3` (moved out of the playlist 2026-11-04) | Fantasy Adventure Quest | alex-morgan | https://pixabay.com/music/adventure-fantasy-adventure-quest-537478/ | Free for use under the Pixabay Content License | **Content ID Registered**; AI generated | 2026-11-04 |
| `backgroundmusicmaster-fantasy-craft-loop-431346.mp3` | Fantasy Craft Loop | BackgroundMusicMaster | https://pixabay.com/music/fantasy-dreamy-childrens-fantasy-craft-loop-431346/ | Free for use under the Pixabay Content License | AI generated | 2026-11-04 |
| `gavinnellist-fantasy-relaxation-music-111778.mp3` | Fantasy Relaxation Music | GavinNellist | https://pixabay.com/music/fantasy-dreamy-childrens-fantasy-relaxation-music-111778/ | Free for use under the Pixabay Content License | none | 2026-11-04 |
| `menieldm-shadows-beneath-the-keep-495833.mp3` | Shadows Beneath the Keep | MenielDM | https://pixabay.com/music/fantasy-dreamy-childrens-shadows-beneath-the-keep-495833/ | Free for use under the Pixabay Content License | none | 2026-11-04 |

How these were traced: Pixabay names downloads `artist-title-ID`, and the ID is the last number in the track page's
address. Each page was opened and its license line and labels read. File sizes also match the page durations
(about 250 kbps), so the files are the tracks the pages describe. The pages were read through a summarising tool,
not the legally binding license text (Pixabay's Terms of Service), so treat this as a good check, not legal advice.

**Content ID Registered** means the track is in YouTube's Content ID system, so streaming it on YouTube can trigger a
claim or a mute even though Pixabay lets you use it. Keep those tracks out of the playlist (move them into a
subfolder such as `assets/music/held/`; only files directly in this folder are played).

Skip anything that is not clearly free to use in a stream, anything labelled "editorial" or "Content ID
registered", and anything you only found re-uploaded on another site.
