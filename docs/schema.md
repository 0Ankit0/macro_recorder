# Macro Recorder JSON Schema (v1)

This project stores macros as a **versioned document** (`MacroDocument`) rather than a raw action list.

## Root object: `MacroDocument`

```json
{
  "version": 1,
  "name": "My Macro",
  "created_at": "2026-03-26T01:23:45.000000+00:00",
  "platform": "macOS-14.0-arm64-arm-64bit",
  "screen_size": [1512, 982],
  "actions": []
}
```

### Fields

- `version` (`int`): Document format version. Current value is `1`.
- `name` (`string`): User-friendly macro name.
- `created_at` (`string`): ISO-8601 timestamp.
- `platform` (`string`): Platform string captured when created.
- `screen_size` (`[int, int]`): Width and height of capture screen.
- `actions` (`MacroAction[]`): Normalized timeline actions.

## `MacroAction` union

Each action contains `t_ms` (milliseconds from macro start) and a `kind`.

### Mouse move

```json
{ "t_ms": 25, "kind": "mouse_move", "x": 100, "y": 240 }
```

### Mouse button

```json
{ "t_ms": 420, "kind": "mouse_down", "x": 100, "y": 240, "button": "left" }
{ "t_ms": 455, "kind": "mouse_up", "x": 100, "y": 240, "button": "left" }
```

### Scroll

```json
{ "t_ms": 700, "kind": "scroll", "x": 100, "y": 240, "dx": 0, "dy": -1 }
```

### Keyboard

```json
{ "t_ms": 900, "kind": "key_down", "key": "a" }
{ "t_ms": 940, "kind": "key_up", "key": "a" }
```

### Optional wait

```json
{ "t_ms": 1200, "kind": "wait", "duration_ms": 500 }
```

## Legacy compatibility

The loader accepts legacy files that are list-only JSON arrays with old keys (`type`, `time`, etc.).
On load, those are migrated into the v1 `MacroDocument` structure.
On save, output is always v1 format.
