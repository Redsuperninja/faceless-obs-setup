"""Scene names shown in OBS. "[S]" scenes are reusable building blocks nested
inside the main scenes, so chat and alerts are edited in one place."""

S_BACKGROUND = "[S] Background"
S_ALERTS = "[S] Alerts"
S_SIDEBAR = "[S] Sidebar"  # the right-hand column: art panel (the cam slot), goal bar, chat
S_SIDEBAR_PLAIN = "[S] Sidebar Plain"  # the same column without the art panel: goal bar and a taller chat
S_MUSIC = "[S] Music"  # background music; its volume is the BG Music slider in the OBS mixer
S_AUDIO = "[S] Audio"  # mic, desktop sound; nested into the main scenes
SCENE_STARTING = "Starting Soon"  # plain right-hand column (no art panel)
SCENE_STARTING_CAM = "Starting Soon + Cam"  # with the art panel: the slot for an avatar or face cam
SCENE_GAMEPLAY = "Gameplay"  # game capture, plain right-hand column
SCENE_DISPLAY = "Display"  # screen capture, plain right-hand column
SCENE_GAMEPLAY_CAM = "Gameplay + Cam"  # same, with the art panel: the slot for an avatar or face cam
SCENE_DISPLAY_CAM = "Display + Cam"
SCENE_CHATTING = "Just Chatting"
SCENE_BRB = "Be Right Back"
SCENE_ENDING = "Ending"
SCENE_MONITOR = "Chat Monitor"  # private: for the streamer to read, never for going live
LEGACY_SCENES = ["[S] Chat", "Screen + Chat"]  # old names: never built now, kept so --reset removes them
ALL_SCENES = [S_BACKGROUND, S_ALERTS, S_AUDIO, S_MUSIC, S_SIDEBAR, S_SIDEBAR_PLAIN, SCENE_STARTING, SCENE_STARTING_CAM,
              SCENE_GAMEPLAY, SCENE_DISPLAY, SCENE_GAMEPLAY_CAM, SCENE_DISPLAY_CAM, SCENE_CHATTING, SCENE_BRB,
              SCENE_ENDING, SCENE_MONITOR] + LEGACY_SCENES
