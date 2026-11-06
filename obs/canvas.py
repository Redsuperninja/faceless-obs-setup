"""Build into an extra OBS canvas (e.g. the "Aitum Vertical" canvas) instead of the main one.

OBS's remote control can reach another canvas's scenes if every request names the scene by its
UUID. This wraps the OBS client so the scene builder works unchanged: scene names in, UUIDs out.

OBS keeps scene names per canvas but ONE global list of sources (inputs), so sources built here get a
" (V)" suffix to stay clear of the main canvas's. The wrapper hides that suffix from the builder, and
only ever lists or removes sources that carry it, so a rebuild here cannot touch your main canvas.
"""

from types import SimpleNamespace

SUFFIX = " (V)"
SHARED = ("Game Capture", "Display Capture")  # reused from the main canvas, never copied


def release_shared(cl, canvas_uuid):
    """Take the shared capture sources out of the extra canvas's scenes. Without this a main --reset cannot
    remove them (they are still in use), and OBS then refuses to add the old copies to the rebuilt main scenes."""
    for sc in cl.send("GetSceneList", {"canvasUuid": canvas_uuid}).scenes:
        for it in cl.send("GetSceneItemList", {"sceneUuid": sc["sceneUuid"]}).scene_items:
            if it["sourceName"] in SHARED:
                cl.send("RemoveSceneItem", {"sceneUuid": sc["sceneUuid"], "sceneItemId": it["sceneItemId"]})


def main_has_input(cl, name):
    return any(i["inputName"] == name for i in cl.get_input_list().inputs)


def find_canvas(cl, name):
    """(uuid, video settings) of the canvas called `name`, or None."""
    for c in cl.send("GetCanvasList").canvases:
        if c["canvasName"] == name:
            return c["canvasUuid"], c["canvasVideoSettings"]
    return None


class CanvasClient:
    is_canvas = True

    def __init__(self, cl, canvas_uuid):
        self.cl, self.uuid = cl, canvas_uuid

    def __getattr__(self, name):  # everything else (filters, volume, kinds...) is not per-canvas
        return getattr(self.cl, name)

    def _scenes(self):
        return {s["sceneName"]: s["sceneUuid"] for s in self.cl.send("GetSceneList", {"canvasUuid": self.uuid}).scenes}

    def _uuid(self, scene):
        return self._scenes()[scene]

    def get_scene_list(self):
        r = self.cl.send("GetSceneList", {"canvasUuid": self.uuid})
        return SimpleNamespace(scenes=r.scenes, current_program_scene_name="")

    def create_scene(self, name):
        self.cl.send("CreateScene", {"sceneName": name, "canvasUuid": self.uuid})

    def remove_scene(self, name):
        self.cl.send("RemoveScene", {"sceneUuid": self._uuid(name)})

    def get_scene_item_list(self, scene):
        r = self.cl.send("GetSceneItemList", {"sceneUuid": self._uuid(scene)})
        items = [{**i, "sourceName": i["sourceName"].removesuffix(SUFFIX)} for i in r.scene_items]
        return SimpleNamespace(scene_items=items)

    def create_scene_item(self, scene, source, enabled=True):
        scenes = self._scenes()
        # A scene is looked up by UUID: by name OBS would find the MAIN canvas's scene of the same name.
        if source in scenes:
            ref = {"sourceUuid": scenes[source]}
        else:  # the capture sources are the main canvas's own (a game can only be hooked once)
            ref = {"sourceName": source if source in SHARED else source + SUFFIX}
        return self.cl.send("CreateSceneItem", {"sceneUuid": scenes[scene], "sceneItemEnabled": enabled, **ref})

    def create_input(self, scene, name, kind, settings, enabled=True):
        return self.cl.send("CreateInput", {"sceneUuid": self._uuid(scene), "inputName": name + SUFFIX,
                                            "inputKind": kind, "inputSettings": settings,
                                            "sceneItemEnabled": enabled})

    def set_scene_item_transform(self, scene, item_id, transform):
        self.cl.send("SetSceneItemTransform", {"sceneUuid": self._uuid(scene), "sceneItemId": item_id,
                                               "sceneItemTransform": transform})

    def get_input_list(self, kind=None):
        """Only the sources this wrapper made (suffix hidden)."""
        mine = [{**i, "inputName": i["inputName"].removesuffix(SUFFIX)}
                for i in self.cl.get_input_list(kind).inputs if i["inputName"].endswith(SUFFIX)]
        return SimpleNamespace(inputs=mine)

    def remove_input(self, name):
        # Sources from another canvas can only be removed by UUID, not by name.
        for i in self.cl.get_input_list().inputs:
            if i["inputName"] == name + SUFFIX:
                try:
                    self.cl.send("RemoveInput", {"inputUuid": i["inputUuid"]})
                except Exception:  # noqa: BLE001  (already gone: fine)
                    pass

    def set_current_program_scene(self, name):
        pass  # the plugin decides which vertical scene is live
