# Architecture

The app is split into four subsystems:

1. **Domain + Storage**
   - `macro_recorder/domain/models.py`: data model (`MacroDocument`, `MacroAction`).
   - `macro_recorder/domain/normalize.py`: timestamp normalization, move compression, speed scaling.
   - `macro_recorder/storage/service.py`: save/load and legacy migration.

2. **Input Backends**
   - `macro_recorder/input_backends/pynput_backend.py`
   - Uses `pynput` listeners for global capture and controllers for playback.
   - Filters macro control hotkeys from recorded key events.

3. **Controller + Services**
   - `macro_recorder/app/controller.py`: central app orchestration and event pump.
   - `macro_recorder/app/recording_service.py`: record lifecycle and action normalization pipeline.
   - `macro_recorder/app/playback_service.py`: one-shot playback and interval looping.
   - `macro_recorder/app/countdown.py`: worker-thread countdown with queue events.

4. **UI / Views**
   - `macro_recorder/ui/dashboard.py`: single-window Tk/ttk dashboard.
   - `macro_recorder/ui/app.py`: composition root that wires backends + services + UI.
   - `main.py`: thin launcher only.

## Threading model

- Tk main thread never receives direct updates from worker threads.
- Worker components emit `AppEvent` objects into `queue.Queue`.
- UI polls queue via `root.after(...)` and applies state updates in main thread.

## Core runtime flow

1. User triggers **Record** or **Play**.
2. Controller starts a 3-second countdown.
3. Countdown emits tick events (`*_tick`) and completion event (`*_done`).
4. Controller/service starts backend work.
5. Backends emit progress/action events into queue.
6. UI poll loop consumes events and updates timeline/status/log.

## Safety controls

- Global hotkeys:
  - `Cmd+Shift+R`: toggle recording
  - `Cmd+Shift+P`: play once
  - `Esc`: emergency stop
- Emergency stop cancels countdowns, listeners, playback, and loops.
