# Architecture

The app is split into four subsystems:

1. **Domain + Storage**
   - `macro_recorder/domain/models.py`: data model (`MacroDocument`, `MacroAction`).
   - `macro_recorder/domain/normalize.py`: timestamp normalization, move compression, speed scaling.
   - `macro_recorder/storage/service.py`: save/load and legacy migration.

2. **Input Backends**
   - `macro_recorder/input_backends/pynput_backend.py`
   - Mouse capture/playback still use `pynput` listeners/controllers.
   - Keyboard trust checks use a non-listener probe (`Listener.IS_TRUSTED` or `AXIsProcessTrusted`).
   - A long-lived keyboard monitor drives both global shortcut dispatch and keyboard recording.
   - Registered shortcut chords are normalized and excluded from recorded macro actions.

3. **Controller + Services**
   - `macro_recorder/app/controller.py`: central app orchestration, command dispatch, event pump.
   - `macro_recorder/app/commands.py`: shared shortcut/command registry used by UI + backend.
   - `macro_recorder/app/recording_service.py`: record lifecycle and action normalization pipeline.
   - `macro_recorder/app/playback_service.py`: one-shot playback and interval looping.
   - `macro_recorder/app/countdown.py`: worker-thread countdown with queue events.

4. **UI / Views**
   - `macro_recorder/ui/dashboard.py`: single-window Tk/ttk dashboard.
   - Buttons and shortcut hints are generated from the command registry.
   - Dedicated Shortcuts table shows action, chord, scope, and current status.
   - `macro_recorder/ui/app.py`: composition root that wires backends + services + UI.
   - `main.py`: thin launcher only.

## Shortcut state machine

- `Cmd+Shift+R`: idle → record countdown; recording → stop recording; ignored during playback/loop.
- `Cmd+Shift+P`: idle + actions present → play countdown; ignored during recording/loop.
- `Esc`: always emergency-stop (countdown, recording, playback, loop).

## Fallback behavior

- If keyboard trust is missing or keyboard monitor startup fails:
  - app stays open,
  - backend error event is emitted,
  - global shortcuts are marked unavailable,
  - window-level Tk bindings remain active.
