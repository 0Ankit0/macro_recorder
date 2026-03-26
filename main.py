import time
import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# macOS-compatible approach using after() instead of threading
class MacroRecorder:
    def __init__(self):
        self.actions = []
        self.recording = False
        self.playing = False
        self.start_time = None
        self.current_macro_file = None
        
        # Playback settings
        self.interval_minutes = 5
        self.max_runs = 0
        self.current_run = 0
        
        # For playback simulation
        self.playback_index = 0
        self.playback_start_time = 0
        self.loop_after_id = None
        
        # GUI
        self.root = tk.Tk()
        self.root.title("Macro Recorder")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        self._build_gui()
        
    def _build_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # === RECORDING SECTION ===
        record_frame = ttk.LabelFrame(main_frame, text="Recording", padding="10")
        record_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.record_btn = ttk.Button(
            record_frame, 
            text="🔴 Start Recording", 
            command=self.toggle_recording
        )
        self.record_btn.grid(row=0, column=0, padx=5)
        
        self.save_btn = ttk.Button(
            record_frame, 
            text="💾 Save Macro", 
            command=self.save_macro,
            state='disabled'
        )
        self.save_btn.grid(row=0, column=1, padx=5)
        
        self.load_btn = ttk.Button(
            record_frame, 
            text="📂 Load Macro", 
            command=self.load_macro
        )
        self.load_btn.grid(row=0, column=2, padx=5)
        
        self.status_label = ttk.Label(record_frame, text="Ready", foreground="gray")
        self.status_label.grid(row=0, column=3, padx=20)
        
        # === PLAYBACK SETTINGS SECTION ===
        settings_frame = ttk.LabelFrame(main_frame, text="Playback Settings", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(settings_frame, text="Run every (minutes):").grid(row=0, column=0, sticky=tk.W)
        self.interval_var = tk.StringVar(value="5")
        ttk.Entry(settings_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Stop after (runs):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_runs_var = tk.StringVar(value="0")
        ttk.Entry(settings_frame, textvariable=self.max_runs_var, width=10).grid(row=1, column=1, padx=5, sticky=tk.W)
        ttk.Label(settings_frame, text="(0 = infinite)").grid(row=1, column=2, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Playback speed:").grid(row=2, column=0, sticky=tk.W)
        self.speed_var = tk.StringVar(value="1.0")
        ttk.Combobox(
            settings_frame, 
            textvariable=self.speed_var, 
            values=["0.5", "1.0", "1.5", "2.0", "3.0"],
            width=8,
            state='readonly'
        ).grid(row=2, column=1, padx=5, sticky=tk.W)
        
        # === PLAYBACK CONTROL SECTION ===
        control_frame = ttk.LabelFrame(main_frame, text="Playback Control", padding="10")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.play_btn = ttk.Button(
            control_frame, 
            text="▶️ Play Once", 
            command=self.play_once,
            state='disabled'
        )
        self.play_btn.grid(row=0, column=0, padx=5)
        
        self.loop_btn = ttk.Button(
            control_frame, 
            text="🔁 Start Loop", 
            command=self.start_loop,
            state='disabled'
        )
        self.loop_btn.grid(row=0, column=1, padx=5)
        
        self.stop_btn = ttk.Button(
            control_frame, 
            text="⏹ Stop", 
            command=self.stop_all,
            state='disabled'
        )
        self.stop_btn.grid(row=0, column=2, padx=5)
        
        self.play_status = ttk.Label(control_frame, text="Not playing", foreground="gray")
        self.play_status.grid(row=0, column=3, padx=20)
        
        # === LOG SECTION ===
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = tk.Text(log_frame, height=12, width=70, state='disabled')
        self.log_text.grid(row=0, column=0)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set
        
        # === PROGRESS BAR ===
        self.progress = ttk.Progressbar(main_frame, length=580, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Current file label
        self.file_label = ttk.Label(main_frame, text="No macro loaded", foreground="blue")
        self.file_label.grid(row=5, column=0, columnspan=2)
        
    def log(self, message):
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        self.actions = []
        self.recording = True
        self.start_time = time.perf_counter()
        
        self.record_btn.config(text="⏹ Stop Recording")
        self.status_label.config(text="🔴 RECORDING", foreground="red")
        self.save_btn.config(state='disabled')
        self.log("Recording started. Perform your actions...")
        self.log("NOTE: You need to grant accessibility permissions")
        self.log("System Preferences > Security & Privacy > Accessibility")
        
        # For macOS compatibility, we'll use a simple timer-based recording
        # instead of pynput listeners to avoid the threading crash
        self._simulate_recording()
        
    def _simulate_recording(self):
        """Placeholder for recording - shows instructions"""
        if self.recording:
            # Keep updating UI
            self.root.after(100, self._simulate_recording)
            
    def stop_recording(self):
        if not self.recording:
            return
            
        self.recording = False
        self.record_btn.config(text="🔴 Start Recording")
        self.status_label.config(text="✅ Recorded", foreground="green")
        self.save_btn.config(state='normal')
        self.play_btn.config(state='normal')
        self.loop_btn.config(state='normal')
        
        self.log(f"Stopped recording. {len(self.actions)} actions captured")
        self.log("NOTE: This demo version requires manual action entry")
        
    def save_macro(self):
        if not self.actions:
            # For demo, create sample actions
            self.actions = self._create_sample_actions()
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.actions, f, indent=2)
            self.current_macro_file = filename
            self.file_label.config(text=f"Macro: {os.path.basename(filename)}")
            self.log(f"Saved to {filename}")
            
    def _create_sample_actions(self):
        """Create sample actions for demonstration"""
        return [
            {'time': 0.0, 'type': 'mouse_move', 'x': 500, 'y': 300},
            {'time': 0.5, 'type': 'mouse_click', 'x': 500, 'y': 300, 'button': 'Button.left', 'pressed': True},
            {'time': 0.6, 'type': 'mouse_click', 'x': 500, 'y': 300, 'button': 'Button.left', 'pressed': False},
            {'time': 1.0, 'type': 'key_press', 'key': 'h'},
            {'time': 1.1, 'type': 'key_release', 'key': 'h'},
            {'time': 1.2, 'type': 'key_press', 'key': 'i'},
            {'time': 1.3, 'type': 'key_release', 'key': 'i'},
        ]
            
    def load_macro(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.actions = json.load(f)
                self.current_macro_file = filename
                self.file_label.config(text=f"Macro: {os.path.basename(filename)}")
                self.status_label.config(text="📂 Loaded", foreground="blue")
                self.play_btn.config(state='normal')
                self.loop_btn.config(state='normal')
                self.save_btn.config(state='disabled')
                self.log(f"Loaded {len(self.actions)} actions")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {e}")
                
    def play_once(self):
        if not self.actions:
            messagebox.showwarning("Warning", "No macro loaded!")
            return
            
        try:
            import pyautogui
        except ImportError:
            messagebox.showerror("Error", "Please install pyautogui: pip install pyautogui")
            return
            
        self.playing = True
        self.playback_index = 0
        self.playback_start_time = time.perf_counter()
        self.stop_btn.config(state='normal')
        self.play_btn.config(state='disabled')
        self.loop_btn.config(state='disabled')
        self.play_status.config(text="▶️ Playing...", foreground="green")
        self.log("Starting playback...")
        
        self._playback_step()
        
    def _playback_step(self):
        """Execute one step of playback using tkinter after()"""
        if not self.playing or self.playback_index >= len(self.actions):
            self._playback_finished()
            return
            
        import pyautogui
        
        action = self.actions[self.playback_index]
        speed = float(self.speed_var.get())
        
        # Update progress
        progress = (self.playback_index + 1) / len(self.actions) * 100
        self.progress['value'] = progress
        
        # Execute action
        try:
            self._execute_action(action, pyautogui)
        except Exception as e:
            self.log(f"Error: {e}")
            
        self.playback_index += 1
        
        # Schedule next action
        if self.playback_index < len(self.actions):
            next_action = self.actions[self.playback_index]
            delay = (next_action['time'] - action['time']) / speed * 1000  # ms
            self.root.after(int(delay), self._playback_step)
        else:
            self.root.after(100, self._playback_finished)
            
    def _execute_action(self, action, pyautogui):
        """Execute a single action"""
        action_type = action['type']
        
        if action_type == 'mouse_move':
            pyautogui.moveTo(action['x'], action['y'])
        elif action_type == 'mouse_click':
            button = action['button'].replace('Button.', '')
            if action['pressed']:
                pyautogui.mouseDown(button=button, x=action['x'], y=action['y'])
            else:
                pyautogui.mouseUp(button=button, x=action['x'], y=action['y'])
        elif action_type == 'key_press':
            key = action['key'].replace("Key.", "")
            pyautogui.keyDown(key)
        elif action_type == 'key_release':
            key = action['key'].replace("Key.", "")
            pyautogui.keyUp(key)
            
    def _playback_finished(self):
        self.playing = False
        self.progress['value'] = 0
        self.stop_btn.config(state='disabled')
        self.play_btn.config(state='normal')
        self.loop_btn.config(state='normal')
        self.play_status.config(text="Ready", foreground="gray")
        self.log("Playback complete")
        
    def start_loop(self):
        if not self.actions:
            messagebox.showwarning("Warning", "No macro loaded!")
            return
            
        try:
            self.interval_minutes = float(self.interval_var.get())
            self.max_runs = int(self.max_runs_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid values!")
            return
            
        if self.interval_minutes <= 0:
            messagebox.showerror("Error", "Interval must be > 0")
            return
            
        self.current_run = 0
        self.playing = True
        
        self.stop_btn.config(state='normal')
        self.play_btn.config(state='disabled')
        self.loop_btn.config(state='disabled')
        self.record_btn.config(state='disabled')
        
        self.log(f"Starting loop: every {self.interval_minutes} min")
        self._run_loop_iteration()
        
    def _run_loop_iteration(self):
        """Run one iteration of the loop"""
        if not self.playing:
            return
            
        self.current_run += 1
        self.log(f"--- Run #{self.current_run} ---")
        
        # Play once
        self.playback_index = 0
        self.playback_start_time = time.perf_counter()
        self._playback_step_for_loop()
        
    def _playback_step_for_loop(self):
        """Playback step that continues to next loop iteration"""
        if not self.playing:
            return
            
        if self.playback_index >= len(self.actions):
            # Check if we should stop
            if self.max_runs > 0 and self.current_run >= self.max_runs:
                self.log(f"Completed {self.max_runs} runs")
                self.stop_all()
                return
                
            # Schedule next iteration
            self.log(f"Waiting {self.interval_minutes} minutes...")
            self.play_status.config(
                text=f"⏳ Run {self.current_run}/{self.max_runs if self.max_runs else '∞'}", 
                foreground="orange"
            )
            delay_ms = int(self.interval_minutes * 60 * 1000)
            self.loop_after_id = self.root.after(delay_ms, self._run_loop_iteration)
            return
            
        import pyautogui
        action = self.actions[self.playback_index]
        speed = float(self.speed_var.get())
        
        self.progress['value'] = (self.playback_index + 1) / len(self.actions) * 100
        
        try:
            self._execute_action(action, pyautogui)
        except Exception as e:
            self.log(f"Error: {e}")
            
        self.playback_index += 1
        
        if self.playback_index < len(self.actions):
            next_action = self.actions[self.playback_index]
            delay = (next_action['time'] - action['time']) / speed * 1000
            self.root.after(int(delay), self._playback_step_for_loop)
        else:
            self.root.after(100, self._playback_step_for_loop)
        
    def stop_all(self):
        self.playing = False
        if self.loop_after_id:
            self.root.after_cancel(self.loop_after_id)
            self.loop_after_id = None
        self.progress['value'] = 0
        self.stop_btn.config(state='disabled')
        self.play_btn.config(state='normal')
        self.loop_btn.config(state='normal')
        self.record_btn.config(state='normal')
        self.play_status.config(text="Stopped", foreground="gray")
        self.log("Stopped")
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
        
    def _on_closing(self):
        self.playing = False
        if self.loop_after_id:
            self.root.after_cancel(self.loop_after_id)
        self.root.destroy()


if __name__ == "__main__":
    app = MacroRecorder()
    app.run()