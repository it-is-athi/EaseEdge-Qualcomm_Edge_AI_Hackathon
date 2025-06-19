import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
import threading
import winsound
from PIL import Image, ImageTk
import cv2
import numpy as np
from recognizer import SpeechRecognitionEngine
from scheduler import TaskScheduler
import time
import pyttsx3

# Initialize the TTS engine once (at the top of your class or module)
tts_engine = pyttsx3.init()

class EmergencySoundTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Emergency Sound Tracker")
        self.geometry("1000x700")
        self.resizable(False, False)

        self.model_path = "vosk-model-small-en-us-0.15"
        self.alert_sound = os.path.join(os.path.dirname(__file__), "alarm.wav")
        self.emergency_keywords = {"help", "fire", "emergency", "water", "food", "medicine"}
        self.engine = None

        self.gesture_thread = None
        self.gesture_running = False
        self.camera_running = False
        self.cap = None
        self.camera_thread = None
        self.detector = None
        self.frame_image = None

        # --- Layout ---
        self._setup_layout()
        self._update_clock()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_layout(self):
        # Top-level grid layout
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Title at the top, spanning both columns
        title_label = tk.Label(self, text="Emergency Sound Tracker", font=("Arial", 22, "bold"), fg="#003366", bg="#f8f9fa")
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Sidebar for controls (left)
        sidebar = tk.Frame(self, width=240, bg="#e3e6ea", bd=0, relief=tk.FLAT)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 0), pady=(0, 0))
        sidebar.grid_propagate(False)

        # Main area (camera + log) in a nested frame
        main_area = tk.Frame(self, bg="#ffffff")
        main_area.grid(row=1, column=1, sticky="nsew", padx=(0, 0), pady=(0, 0))
        main_area.grid_rowconfigure(0, weight=3)
        main_area.grid_rowconfigure(1, weight=2)
        main_area.grid_columnconfigure(0, weight=1)

        # Camera feed at the top of main area (3/5)
        self.camera_width = 640
        self.camera_height = 360
        self.camera_frame = tk.Frame(main_area, bg="#222", highlightbackground="#bbb", highlightthickness=1)
        self.camera_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=(30, 10))
        self.camera_frame.grid_propagate(False)
        self.camera_canvas = tk.Canvas(self.camera_frame, bg="#222", width=self.camera_width, height=self.camera_height, highlightthickness=0)
        self.camera_canvas.pack(expand=False, fill=tk.NONE)
        self._show_placeholder_camera()

        # System log below camera feed (2/5)
        log_frame = tk.Frame(main_area, bg="#f8f9fa", highlightbackground="#bbb", highlightthickness=1)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        log_label = tk.Label(log_frame, text="Recognition Log", font=("Arial", 14, "bold"), fg="#003366", bg="#f8f9fa")
        log_label.pack(pady=(12, 0))
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Courier", 11), height=10, width=60, bg="#f8f9fa", bd=0, relief=tk.FLAT)
        self.log_text.pack(pady=8, padx=8, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # Sidebar content (with more spacing and section headers)
        self.clock_label = tk.Label(sidebar, text="", font=("Arial", 15, "bold"), fg="#003366", bg="#e3e6ea")
        self.clock_label.pack(pady=(30, 10))

        section1 = tk.Label(sidebar, text="Speech Controls", font=("Arial", 12, "bold"), fg="#607D8B", bg="#e3e6ea")
        section1.pack(pady=(10, 2))
        self.start_button = tk.Button(sidebar, text="Start Listening", width=20, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=self._toggle_listening, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.start_button.pack(pady=6)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = tk.Entry(sidebar, textvariable=self.keyword_var, font=("Arial", 12), width=18, bd=1, relief=tk.GROOVE)
        self.keyword_entry.pack(pady=4)
        self.add_button = tk.Button(sidebar, text="Add Keyword", bg="#2196F3", fg="white", font=("Arial", 12, "bold"), command=self._add_keyword, width=20, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.add_button.pack(pady=6)

        section2 = tk.Label(sidebar, text="Camera & Gestures", font=("Arial", 12, "bold"), fg="#607D8B", bg="#e3e6ea")
        section2.pack(pady=(18, 2))
        self.camera_button = tk.Button(sidebar, text="Start Camera", width=20, bg="#FFC107", fg="black", font=("Arial", 12, "bold"), command=self._toggle_camera, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.camera_button.pack(pady=6)
        self.gesture_button = tk.Button(sidebar, text="Start Gesture Detection", width=20, bg="#607D8B", fg="white", font=("Arial", 12, "bold"), command=self._toggle_gesture_detection, state=tk.DISABLED, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.gesture_button.pack(pady=6)

        section3 = tk.Label(sidebar, text="Reminders", font=("Arial", 12, "bold"), fg="#607D8B", bg="#e3e6ea")
        section3.pack(pady=(18, 2))
        self.add_task_btn = tk.Button(sidebar, text="Add Reminder", bg="#FF9800", fg="white", font=("Arial", 12, "bold"), command=self._add_scheduled_task, width=20, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.add_task_btn.pack(pady=6)
        self.view_tasks_btn = tk.Button(sidebar, text="View Reminders", bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), command=self._view_scheduled_tasks, width=20, bd=0, relief=tk.FLAT, highlightthickness=0)
        self.view_tasks_btn.pack(pady=6)

        # Scheduler
        self.scheduler = TaskScheduler(read_aloud_callback=self._read_aloud)
        self.scheduler.start()
        self.after(1000, self._check_scheduled_tasks)

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=f"Current Time: {now}")
        self.after(1000, self._update_clock)

    def _toggle_camera(self):
        if self.camera_running:
            self.camera_running = False
            self.camera_button.config(text="Start Camera", bg="#FFC107")
            self._log_message("Camera stopped.")
            self.gesture_button.config(state=tk.DISABLED)
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=1)
            self._show_placeholder_camera()
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self._log_message("Failed to start camera.", is_alert=True)
                self.cap = None
                return
            self.camera_running = True
            self.camera_button.config(text="Stop Camera", bg="#f44336")
            self._log_message("Camera started.")
            self.gesture_button.config(state=tk.NORMAL)
            self.camera_thread = threading.Thread(target=self._show_camera_feed, daemon=True)
            self.camera_thread.start()

    def _show_camera_feed(self):
        while self.camera_running and self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            # If gesture detection is running, let that thread handle the display
            if not self.gesture_running:
                self._update_camera_label(frame)
            cv2.waitKey(10)
            time.sleep(0.03)  # Limit update rate to reduce flicker
        self.camera_canvas.delete("all")

    def _update_camera_label(self, frame):
        # Convert OpenCV BGR to RGB and then to ImageTk
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((self.camera_width, self.camera_height))
        imgtk = ImageTk.PhotoImage(image=img)
        self.frame_image = imgtk  # Prevent garbage collection
        self.camera_canvas.delete("all")  # Clear previous image to prevent flicker
        self.camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

    def _toggle_gesture_detection(self):
        if not self.camera_running or self.cap is None:
            self._log_message("Camera must be started before gesture detection.", is_alert=True)
            return
        if self.gesture_running:
            self.gesture_running = False
            self.gesture_button.config(text="Start Gesture Detection", bg="#607D8B")
            self._log_message("Stopped gesture detection.")
        else:
            self.gesture_running = True
            self.gesture_button.config(text="Stop Gesture Detection", bg="#f44336")
            self._log_message("Started gesture detection.")
            self.gesture_thread = threading.Thread(target=self._run_gesture_detection, daemon=True)
            self.gesture_thread.start()

    def _run_gesture_detection(self):
        try:
            from gesture_detector import GestureDetector
            self.detector = GestureDetector()
            while self.gesture_running and self.camera_running and self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                processed_frame = self.detector.process_frame(frame)
                self._update_camera_label(processed_frame)
                cv2.waitKey(10)
            self.detector = None
        except Exception as e:
            self._log_message(f"Gesture detection error: {e}", is_alert=True)
        finally:
            self.gesture_running = False
            self.gesture_button.config(text="Start Gesture Detection", bg="#607D8B")

    def _check_scheduled_tasks(self):
        """Check for any triggered tasks (called periodically)"""
        tasks = self.scheduler.check_for_tasks()
        for task in tasks:
            self._log_message(f"REMINDER: {task['name']}", is_alert=True)
            threading.Thread(
                target=lambda: winsound.PlaySound(self.alert_sound, winsound.SND_FILENAME | winsound.SND_ASYNC),
                daemon=True
            ).start()
            messagebox.showwarning("Reminder", task['name'])
        
        # Check again in 1 second
        self.after(1000, self._check_scheduled_tasks)

    def _add_scheduled_task(self):
        """Open dialog to add a new scheduled task"""
        task_name = simpledialog.askstring("Add Reminder", "Enter reminder text:")
        if not task_name:
            return
            
        task_time = simpledialog.askstring("Add Reminder", "Enter time (HH:MM):")
        if not task_time:
            return
            
        repeat = messagebox.askyesno("Add Reminder", "Repeat daily?")
        
        try:
            # Validate time format
            datetime.strptime(task_time, "%H:%M")
            self.scheduler.add_task(task_name, task_time, repeat)
            self._log_message(f"Added reminder: {task_name} at {task_time}")
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Please use HH:MM")

    def _view_scheduled_tasks(self):
        """Show all scheduled tasks"""
        tasks = self.scheduler.get_tasks()
        if not tasks:
            messagebox.showinfo("Scheduled Reminders", "No reminders scheduled")
            return
            
        task_list = "\n".join([f"{t['name']} at {t['time']} (daily: {t['repeat']})" for t in tasks])
        messagebox.showinfo("Scheduled Reminders", task_list)

    def _read_aloud(self, text):
        self._log_message(f"Reading aloud: {text}", is_alert=True)
        # Play alert sound (if you want)
        threading.Thread(
            target=lambda: winsound.PlaySound(self.alert_sound, winsound.SND_FILENAME | winsound.SND_ASYNC),
            daemon=True
        ).start()
        # Speak the text
        threading.Thread(
            target=lambda: tts_engine.say(text) or tts_engine.runAndWait(),
            daemon=True
        ).start()

    def _toggle_listening(self):
        if self.engine and self.engine.is_running:
            self.engine.stop()
            self.engine = None
            self.start_button.config(text="Start Listening", bg="#4CAF50")
            self._log_message("Stopped listening.")
        else:
            try:
                self.engine = SpeechRecognitionEngine(model_path=self.model_path)
                self.engine.start(self._on_text_recognized)
                self.start_button.config(text="Stop Listening", bg="#f44336")
                self._log_message("Started listening.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_text_recognized(self, text):
        self._log_message(f"Recognized: {text}")
        words = text.lower().split()
        found = self.emergency_keywords.intersection(words)
        if found:
            keyword_str = ", ".join(found)
            self._log_message(f"🚨 ALERT: {keyword_str.upper()} DETECTED!", is_alert=True)
            threading.Thread(
                target=lambda: winsound.PlaySound(self.alert_sound, winsound.SND_FILENAME | winsound.SND_ASYNC),
                daemon=True
            ).start()
            messagebox.showwarning("Emergency", f"Detected: {keyword_str.upper()}")

    def _log_message(self, message, is_alert=False):
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = "alert" if is_alert else "normal"
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)

        if is_alert:
            self.log_text.tag_config("alert", foreground="red", font=("Courier", 11, "bold"))
        else:
            self.log_text.tag_config("normal", foreground="black")

        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _add_keyword(self):
        keyword = self.keyword_var.get().strip().lower()
        if keyword:
            self.emergency_keywords.add(keyword)
            self._log_message(f"Added keyword: {keyword}")
            self.keyword_var.set("")

    def _on_close(self):
        """Handle window closing"""
        if self.engine and self.engine.is_running:
            self.engine.stop()
        if hasattr(self, 'scheduler'):
            self.scheduler.stop()
        self.destroy()

    def _show_placeholder_camera(self):
        # Create a blank (black) image as a placeholder
        blank = np.zeros((self.camera_height, self.camera_width, 3), dtype=np.uint8)
        img = Image.fromarray(blank)
        imgtk = ImageTk.PhotoImage(image=img)
        self.frame_image = imgtk  # Prevent garbage collection
        self.camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

if __name__ == "__main__":
    app = EmergencySoundTracker()
    app.mainloop()