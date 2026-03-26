from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from macro_recorder.app.controller import AppController
from macro_recorder.domain.models import action_label


class MacroDashboard:
    def __init__(self, root: tk.Tk, controller: AppController, permissions_ok: bool):
        self.root = root
        self.controller = controller
        self.permissions_ok = permissions_ok
        self.mode_var = tk.StringVar(value="Idle")
        self.banner_var = tk.StringVar(value="Ready")
        self.file_var = tk.StringVar(value="No file loaded")
        self.count_var = tk.StringVar(value="0 actions")
        self.duration_var = tk.StringVar(value="0.00s")
        self.permission_var = tk.StringVar(value="Trusted" if permissions_ok else "Missing macOS Input Monitoring")
        self.name_var = tk.StringVar(value=controller.document.name)
        self.interval_var = tk.StringVar(value="5")
        self.max_runs_var = tk.StringVar(value="0")
        self.speed_var = tk.StringVar(value="1.0")
        self.log_lines: list[str] = []
        self._build()
        self._bind_hotkeys()
        self._poll_queue()

    def _build(self) -> None:
        self.root.title("Macro Recorder")
        self.root.geometry("1100x700")
        style = ttk.Style()
        style.configure("Card.TLabelframe", padding=12)

        shell = ttk.Frame(self.root, padding=12)
        shell.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(shell)
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, textvariable=self.permission_var).pack(side=tk.LEFT)
        ttk.Label(header, text="  |  ").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.name_var).pack(side=tk.LEFT)
        ttk.Label(header, text="  |  ").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.count_var).pack(side=tk.LEFT)
        ttk.Label(header, text="  |  ").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.duration_var).pack(side=tk.LEFT)
        ttk.Label(header, text="  |  ").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.file_var).pack(side=tk.LEFT)

        content = ttk.Panedwindow(shell, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content)
        right = ttk.Frame(content)
        content.add(left, weight=2)
        content.add(right, weight=3)

        rec = ttk.LabelFrame(left, text="Record", style="Card.TLabelframe")
        rec.pack(fill=tk.X, pady=6)
        self.record_btn = ttk.Button(rec, text="Start Recording", command=self.on_record_toggle)
        self.record_btn.pack(fill=tk.X, pady=4)
        if not self.permissions_ok:
            self.record_btn.configure(state=tk.DISABLED)
            ttk.Label(rec, text="Enable System Settings → Privacy & Security → Input Monitoring and Accessibility.").pack(fill=tk.X)

        run = ttk.LabelFrame(left, text="Run Once / Loop", style="Card.TLabelframe")
        run.pack(fill=tk.X, pady=6)
        ttk.Button(run, text="Play Once", command=self.on_play_once).pack(fill=tk.X, pady=4)
        ttk.Label(run, text="Interval minutes").pack(anchor=tk.W)
        ttk.Entry(run, textvariable=self.interval_var).pack(fill=tk.X)
        ttk.Label(run, text="Stop after runs (0=∞)").pack(anchor=tk.W)
        ttk.Entry(run, textvariable=self.max_runs_var).pack(fill=tk.X)
        ttk.Label(run, text="Speed").pack(anchor=tk.W)
        ttk.Combobox(run, values=["0.5", "1.0", "1.5", "2.0"], textvariable=self.speed_var, state="readonly").pack(fill=tk.X)
        ttk.Button(run, text="Start Loop", command=self.on_start_loop).pack(fill=tk.X, pady=4)
        ttk.Button(run, text="Emergency Stop (Esc)", command=self.on_emergency_stop).pack(fill=tk.X)

        settings = ttk.LabelFrame(left, text="Settings", style="Card.TLabelframe")
        settings.pack(fill=tk.X, pady=6)
        ttk.Entry(settings, textvariable=self.name_var).pack(fill=tk.X, pady=4)
        ttk.Button(settings, text="Save", command=self.on_save).pack(fill=tk.X, pady=2)
        ttk.Button(settings, text="Load", command=self.on_load).pack(fill=tk.X, pady=2)

        timeline = ttk.LabelFrame(right, text="Timeline Inspector", style="Card.TLabelframe")
        timeline.pack(fill=tk.BOTH, expand=True, pady=6)
        self.tree = ttk.Treeview(timeline, columns=("time", "action", "details"), show="headings", height=20)
        for col, heading in (("time", "Time"), ("action", "Action"), ("details", "Details")):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=150 if col != "details" else 350)
        self.tree.pack(fill=tk.BOTH, expand=True)
        btn_row = ttk.Frame(timeline)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Delete Selected", command=self.on_delete_selected).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Clear All", command=self.on_clear_all).pack(side=tk.LEFT)

        bottom = ttk.Frame(shell)
        bottom.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(bottom, textvariable=self.mode_var).pack(side=tk.LEFT)
        ttk.Label(bottom, text=" | ").pack(side=tk.LEFT)
        ttk.Label(bottom, textvariable=self.banner_var).pack(side=tk.LEFT)
        self.log = tk.Text(shell, height=6)
        self.log.pack(fill=tk.X)

    def _bind_hotkeys(self) -> None:
        self.root.bind_all("<Command-Shift-R>", lambda _: self.on_record_toggle())
        self.root.bind_all("<Command-Shift-P>", lambda _: self.on_play_once())
        self.root.bind_all("<Escape>", lambda _: self.on_emergency_stop())

    def on_record_toggle(self) -> None:
        if self.controller.recording.is_recording:
            self.controller.stop_recording()
            self.record_btn.configure(text="Start Recording")
        else:
            self.banner_var.set("Recording starts in 3...")
            self.controller.start_record_countdown()

    def on_play_once(self) -> None:
        self.banner_var.set("Playback starts in 3...")
        self.controller.start_play_countdown()

    def on_start_loop(self) -> None:
        self.controller.start_loop(float(self.interval_var.get()), int(self.max_runs_var.get()), float(self.speed_var.get()))
        self.mode_var.set("Looping")

    def on_emergency_stop(self) -> None:
        self.controller.emergency_stop()

    def on_save(self) -> None:
        self.controller.document.name = self.name_var.get().strip() or "Untitled Macro"
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.controller.save(path)

    def on_load(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self.controller.load(path)
            self.name_var.set(self.controller.document.name)
            self._refresh_table()

    def on_delete_selected(self) -> None:
        selected = self.tree.selection()
        idxs = sorted((int(self.tree.item(item, "text")) for item in selected), reverse=True)
        for idx in idxs:
            if 0 <= idx < len(self.controller.document.actions):
                self.controller.document.actions.pop(idx)
        self._refresh_table()

    def on_clear_all(self) -> None:
        self.controller.document.actions.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, action in enumerate(self.controller.document.actions):
            details = action_label(action)
            self.tree.insert("", tk.END, text=str(idx), values=(f"{action['t_ms']} ms", action["kind"], details))
        self.count_var.set(f"{len(self.controller.document.actions)} actions")
        self.duration_var.set(f"{self.controller.document.duration_ms/1000:.2f}s")

    def _poll_queue(self) -> None:
        for event in self.controller.pump_events():
            self._handle_event(event.type, event.payload)
        self.root.after(50, self._poll_queue)

    def _handle_event(self, event_type: str, payload: dict) -> None:
        if event_type == "record_tick":
            self.banner_var.set(f"Recording starts in {payload['remaining']}...")
        elif event_type == "record_done":
            self.root.iconify()
            self.controller.start_recording_now()
            self.record_btn.configure(text="Stop Recording")
            self.mode_var.set("Recording")
        elif event_type == "play_tick":
            self.banner_var.set(f"Playback starts in {payload['remaining']}...")
        elif event_type == "play_done":
            self.mode_var.set("Idle")
            self.banner_var.set("Playback complete")
        elif event_type == "play_progress":
            self.mode_var.set(f"Playing {payload['index']}/{payload['total']}")
        elif event_type == "record_action":
            self._refresh_table()
        elif event_type == "record_stopped":
            self.mode_var.set("Idle")
            self.banner_var.set(f"Recorded {payload['count']} actions")
            self._refresh_table()
        elif event_type == "document_loaded":
            self.file_var.set(payload["path"])
            self.banner_var.set(f"Loaded {payload['count']} actions")
        elif event_type == "document_saved":
            self.file_var.set(payload["path"])
            self.banner_var.set("Saved")
        elif event_type == "emergency_stopped":
            self.mode_var.set("Stopped")
            self.banner_var.set("Emergency stop")

        self.log.insert(tk.END, f"{event_type} {payload}\n")
        self.log.see(tk.END)
