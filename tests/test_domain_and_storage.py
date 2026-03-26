from macro_recorder.domain.normalize import MouseMoveCompressor, scale_actions
from macro_recorder.storage.service import StorageService


def test_mouse_move_compression_keeps_click_context():
    actions = [
        {"t_ms": 0, "kind": "mouse_move", "x": 10, "y": 10},
        {"t_ms": 5, "kind": "mouse_move", "x": 10, "y": 10},
        {"t_ms": 10, "kind": "mouse_move", "x": 11, "y": 11},
        {"t_ms": 15, "kind": "mouse_down", "x": 11, "y": 11, "button": "left"},
    ]
    compressed = MouseMoveCompressor(min_interval_ms=25).compress(actions)
    assert compressed[-2]["kind"] == "mouse_move"
    assert compressed[-1]["kind"] == "mouse_down"


def test_speed_scaling():
    actions = [{"t_ms": 1000, "kind": "key_down", "key": "a"}]
    scaled = scale_actions(actions, speed=2.0)
    assert scaled[0]["t_ms"] == 500


def test_legacy_json_migration(tmp_path):
    legacy = [
        {"time": 0.0, "type": "key_press", "key": "a"},
        {"time": 0.1, "type": "key_release", "key": "a"},
    ]
    path = tmp_path / "old.json"
    path.write_text(__import__("json").dumps(legacy))
    doc = StorageService().load(str(path))
    assert doc.version == 1
    assert doc.actions[0]["kind"] == "key_down"
    assert doc.actions[1]["kind"] == "key_up"
