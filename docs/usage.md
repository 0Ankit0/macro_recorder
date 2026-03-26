# Product Usage Guide

## 1) Setup (Python 3.13)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or install with project metadata:

```bash
pip install -e .[dev]
```

## 2) Run

```bash
python main.py
```

## 3) macOS permissions

For global keyboard/mouse capture, macOS requires trust permissions.

Enable:
- **System Settings → Privacy & Security → Input Monitoring**
- **System Settings → Privacy & Security → Accessibility**

If trust is missing (or keyboard backend fails), the app still runs and falls back to window-only shortcuts with a clear status banner.

## 4) Record a macro

1. Click **Start Recording (Cmd+Shift+R)**.
2. Wait for the 3-second countdown.
3. Perform mouse/keyboard actions.
4. Stop recording with button or `Cmd+Shift+R`.
5. Review actions in the timeline inspector.

## 5) Save and load

- **Save** writes v1 JSON schema.
- **Load** accepts both legacy list-only JSON and v1 documents.

## 6) Playback

- **Play Once (Cmd+Shift+P)** triggers a 3-second safety countdown then runs actions.
- **Start Loop** runs repeated playback with interval controls:
  - `Interval minutes`
  - `Stop after runs` (`0` = infinite)
  - `Speed`

## 7) Emergency stop

- Press `Esc` or click **Emergency Stop (Esc)** to cancel active countdown, recording, playback, or loop.

## 8) Shortcuts section

The dashboard includes a **Shortcuts** section with:
- action,
- shortcut chord,
- scope (`Global` or `Window`),
- status (`Ready`, `Needs permissions`, `Unavailable`).

## 9) Timeline inspector

- Shows `Time`, `Action`, and `Details` columns.
- Supports:
  - **Delete Selected**
  - **Clear All**
  - Macro name editing via settings panel.

## 10) Tests

```bash
pytest -q
```
