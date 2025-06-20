import os
import tkinter as tk
import tkinter.ttk as ttk
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
import customtkinter as ctk

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

        # Theme colors (moved to class scope)
        self.accent = "#009688"  # Teal
        self.accent_dark = "#00796b"
        self.accent_light = "#4dd0e1"  # Aqua
        self.bg_light = "#f8f9fa"
        self.sidebar_bg = "#e0f2f1"
        self.card_border = "#b2dfdb"
        self.text_dark = "#004d40"
        self.btn_radius = 20

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

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=("Segoe UI", 12, "bold"), padding=10, borderwidth=0, focusthickness=3, focuscolor=self.accent)
        style.map('TButton',
            background=[('active', self.accent_dark), ('!active', self.accent)],
            foreground=[('disabled', '#ffffff'), ('!disabled', '#ffffff')],
            relief=[('pressed', 'flat'), ('!pressed', 'flat')]
        )
        style.configure('Accent.TButton', background=self.accent, foreground='#ffffff', borderwidth=0, relief='flat')
        style.map('Accent.TButton', background=[('active', self.accent_dark), ('!active', self.accent)])
        style.configure('Light.TButton', background=self.accent_light, foreground=self.text_dark, borderwidth=0, relief='flat')
        style.map('Light.TButton', background=[('active', self.accent), ('!active', self.accent_light)])
        style.configure('Dark.TButton', background=self.accent_dark, foreground='#ffffff', borderwidth=0, relief='flat')
        style.map('Dark.TButton', background=[('active', self.accent), ('!active', self.accent_dark)])
        style.configure('Danger.TButton', background='#e53935', foreground='#ffffff', borderwidth=0, relief='flat')
        style.map('Danger.TButton', background=[('active', '#b71c1c'), ('!active', '#e53935')])

        # Title at the top, spanning both columns
        title_label = tk.Label(self, text="Emergency Sound Tracker", font=("Segoe UI", 26, "bold"), fg=self.accent, bg=self.bg_light)
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        # Sidebar for controls (left) as a Material card with scrollable content and gradient
        sidebar_frame = tk.Frame(self, width=260, bg=self.sidebar_bg, bd=0, relief=tk.FLAT, highlightbackground=self.card_border, highlightthickness=2)
        sidebar_frame.grid(row=1, column=0, sticky="nsw", padx=(18, 0), pady=(18, 18))
        sidebar_frame.grid_propagate(False)
        # Gradient background
        sidebar_gradient = tk.Canvas(sidebar_frame, width=260, height=1000, highlightthickness=0, bd=0)
        sidebar_gradient.pack(fill='both', expand=True)
        for i in range(100):
            color = f'#{int(224-(i*1.2)):02x}{242-int(i*1.2):02x}{241-int(i*1.2):02x}'
            sidebar_gradient.create_rectangle(0, i*10, 260, (i+1)*10, outline='', fill=color)
        # Sidebar content in a scrollable canvas
        sidebar_canvas = tk.Canvas(sidebar_frame, bg=self.sidebar_bg, width=260, highlightthickness=0, bd=0)
        sidebar_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        sidebar_scrollbar = tk.Scrollbar(sidebar_frame, orient='vertical', command=sidebar_canvas.yview)
        sidebar_scrollbar.place(relx=1, rely=0, relheight=1, anchor='ne')
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        sidebar_content = tk.Frame(sidebar_canvas, bg=self.sidebar_bg)
        sidebar_canvas.create_window((0, 0), window=sidebar_content, anchor='nw')
        def _on_sidebar_configure(event):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox('all'))
        sidebar_content.bind('<Configure>', _on_sidebar_configure)
        sidebar = sidebar_content

        # Main area (camera + log) in a nested frame as a Material card
        main_area = tk.Frame(self, bg=self.bg_light, highlightbackground=self.card_border, highlightthickness=2)
        main_area.grid(row=1, column=1, sticky="nsew", padx=(0, 18), pady=(18, 18))
        main_area.grid_rowconfigure(0, weight=3)
        main_area.grid_rowconfigure(1, weight=2)
        main_area.grid_columnconfigure(0, weight=1)

        # Camera feed at the top of main area (3/5)
        self.camera_width = 640
        self.camera_height = 360
        self.camera_frame = tk.Frame(main_area, bg="#222", highlightbackground=self.accent_light, highlightthickness=2)
        self.camera_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=(30, 10))
        self.camera_frame.grid_propagate(False)
        self.camera_canvas = tk.Canvas(self.camera_frame, bg="#222", width=self.camera_width, height=self.camera_height, highlightthickness=0)
        self.camera_canvas.pack(expand=False, fill=tk.NONE)
        self._show_placeholder_camera()

        # System log below camera feed (2/5)
        log_frame = tk.Frame(main_area, bg=self.bg_light, highlightbackground=self.accent_light, highlightthickness=2)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        log_label = tk.Label(log_frame, text="Recognition Log", font=("Segoe UI", 15, "bold"), fg=self.accent, bg=self.bg_light)
        log_label.pack(pady=(12, 0))
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 11), height=10, width=60, bg=self.bg_light, bd=0, relief=tk.FLAT)
        self.log_text.pack(pady=8, padx=8, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # Sidebar content (with Teal/Aqua theme)
        self.clock_label = ctk.CTkLabel(sidebar, text="", font=("Segoe UI", 15, "bold"), text_color=self.accent, fg_color="transparent")
        self.clock_label.pack(pady=(30, 10))
        section1 = ctk.CTkLabel(sidebar, text="SPEECH CONTROLS", font=("Segoe UI", 11, "bold"), text_color=self.accent_dark, fg_color="transparent")
        section1.pack(pady=(10, 2))
        self.start_button = self._add_icon_button(sidebar, "Start Listening", "🎤", 'Accent.TButton', self._toggle_listening)
        self.start_button.pack(pady=12, ipadx=8, ipady=4, fill='x')
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ctk.CTkEntry(sidebar, textvariable=self.keyword_var, font=("Segoe UI", 12), width=220, fg_color="white", border_width=1, border_color=self.accent_dark, text_color=self.text_dark)
        self.keyword_entry.pack(pady=4, fill='x')
        self.add_button = self._add_icon_button(sidebar, "Add Keyword", "➕", 'Dark.TButton', self._add_keyword)
        self.add_button.pack(pady=12, ipadx=8, ipady=4, fill='x')
        # Divider
        ctk.CTkFrame(sidebar, height=2, fg_color=self.card_border).pack(fill='x', pady=8)
        section2 = ctk.CTkLabel(sidebar, text="CAMERA & GESTURES", font=("Segoe UI", 11, "bold"), text_color=self.accent_dark, fg_color="transparent")
        section2.pack(pady=(10, 2))
        self.camera_button = self._add_icon_button(sidebar, "Start Camera", "📷", 'Accent.TButton', self._toggle_camera)
        self.camera_button.pack(pady=12, ipadx=8, ipady=4, fill='x')
        self.camera_button.configure(fg_color=self.accent, hover_color=self.accent_dark)
        self.gesture_button = self._add_icon_button(sidebar, "Start Gesture Detection", "✋", 'Dark.TButton', self._toggle_gesture_detection)
        self.gesture_button.pack(pady=12, ipadx=8, ipady=4, fill='x')
        self.gesture_button.configure(fg_color=self.accent_dark, hover_color=self.accent)
        # Divider
        ctk.CTkFrame(sidebar, height=2, fg_color=self.card_border).pack(fill='x', pady=8)
        section3 = ctk.CTkLabel(sidebar, text="REMINDERS", font=("Segoe UI", 11, "bold"), text_color=self.accent_dark, fg_color="transparent")
        section3.pack(pady=(10, 2))
        self.add_task_btn = self._add_icon_button(sidebar, "Add Reminder", "⏰", 'Accent.TButton', self._add_scheduled_task)
        self.add_task_btn.pack(pady=12, ipadx=8, ipady=4, fill='x')
        self.view_tasks_btn = self._add_icon_button(sidebar, "View Reminders", "📋", 'Accent.TButton', self._view_scheduled_tasks)
        self.view_tasks_btn.pack(pady=12, ipadx=8, ipady=4, fill='x')
        
        # Scheduler
        self.scheduler = TaskScheduler(read_aloud_callback=self._read_aloud)
        self.scheduler.start()
        self.after(1000, self._check_scheduled_tasks)

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=f"Current Time: {now}")
        self.after(1000, self._update_clock)

    def _toggle_camera(self):
        if self.camera_running:
            self.camera_running = False
            self.camera_button.configure(text="📷  Start Camera", fg_color=self.accent, hover_color=self.accent_dark)
            self._log_message("Camera stopped.")
            self.gesture_button.configure(state='disabled')
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
            self.camera_button.configure(text="⏹️  Stop Camera", fg_color="#e53935", hover_color="#b71c1c")
            self._log_message("Camera started.")
            self.gesture_button.configure(state='normal')
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
            self.gesture_button.configure(text="✋  Start Gesture Detection", fg_color=self.accent_dark, hover_color=self.accent)
            self._log_message("Stopped gesture detection.")
        else:
            self.gesture_running = True
            self.gesture_button.configure(text="⏹️  Stop Gesture Detection", fg_color="#e53935", hover_color="#b71c1c")
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
            self.gesture_button.configure(text="✋  Start Gesture Detection", fg_color=self.accent_dark, hover_color=self.accent)

    def _check_scheduled_tasks(self):
        """Check for any triggered tasks (called periodically)"""
        tasks = self.scheduler.check_for_tasks()
        for task in tasks:
            self._log_message(f"REMINDER: {task['name']}", is_alert=True)
            threading.Thread(
                target=lambda: winsound.PlaySound(self.alert_sound, winsound.SND_FILENAME | winsound.SND_ASYNC),
                daemon=True
            ).start()
            self._show_reminder_popup(task['name'])
        
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
            self._show_reminders_popup(["No reminders scheduled."])
            return
            
        task_list = [f"{t['name']} at {t['time']} (daily: {t['repeat']})" for t in tasks]
        self._show_reminders_popup(task_list)

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
            self.start_button.configure(text="🎤  Start Listening", fg_color=self.accent, hover_color=self.accent_dark)
            self._log_message("Stopped listening.")
        else:
            try:
                self.engine = SpeechRecognitionEngine(model_path=self.model_path)
                self.engine.start(self._on_text_recognized)
                self.start_button.configure(text="⏹️  Stop Listening", fg_color="#e53935", hover_color="#b71c1c")
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

    def _add_icon_button(self, parent, text, icon, style, command, **kwargs):
        btn = ctk.CTkButton(
            parent,
            text=f'{icon}  {text}',
            command=command,
            corner_radius=18,
            fg_color=self.accent if style=="Accent.TButton" else (self.accent_dark if style=="Dark.TButton" else self.sidebar_bg),
            text_color="white" if style!="Light.TButton" else self.accent_dark,
            hover_color=self.accent_dark if style=="Accent.TButton" else self.accent,
            font=("Segoe UI", 13, "bold"),
            **kwargs
        )
        return btn

    def _show_reminder_popup(self, reminder_text):
        popup = ctk.CTkToplevel(self)
        popup.title("⏰ Reminder!")
        popup.geometry("340x200")
        popup.resizable(False, False)
        popup.configure(fg_color=self.sidebar_bg)
        def close_popup():
            self.attributes('-alpha', 1.0)  # Restore main window opacity
            popup.grab_release()
            popup.destroy()
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", close_popup)
        # Emoji
        emoji_label = ctk.CTkLabel(popup, text="⏰", font=("Segoe UI Emoji", 48), text_color=self.accent)
        emoji_label.pack(pady=(18, 0))
        # Reminder text
        reminder_label = ctk.CTkLabel(popup, text=reminder_text, font=("Segoe UI", 20, "bold"), text_color=self.text_dark, wraplength=300)
        reminder_label.pack(pady=(10, 0))
        # Dismiss button
        dismiss_btn = ctk.CTkButton(popup, text="Dismiss", command=close_popup, corner_radius=18, fg_color=self.accent, hover_color=self.accent_dark, font=("Segoe UI", 14, "bold"))
        dismiss_btn.pack(pady=(22, 0), ipadx=10, ipady=4)
        # Center the popup
        self.after(100, lambda: popup.geometry(f"+{self.winfo_x() + self.winfo_width()//2 - 170}+{self.winfo_y() + self.winfo_height()//2 - 100}"))

    def _show_reminders_popup(self, reminders):
        popup = ctk.CTkToplevel(self)
        popup.title("📋 Scheduled Reminders")
        popup.geometry("400x320")
        popup.resizable(False, False)
        popup.configure(fg_color=self.sidebar_bg)
        def close_popup():
            self.attributes('-alpha', 1.0)  # Restore main window opacity
            popup.grab_release()
            popup.destroy()
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", close_popup)
        # Emoji and title
        emoji_label = ctk.CTkLabel(popup, text="📋", font=("Segoe UI Emoji", 40), text_color=self.accent)
        emoji_label.pack(pady=(16, 0))
        title_label = ctk.CTkLabel(popup, text="Scheduled Reminders", font=("Segoe UI", 18, "bold"), text_color=self.text_dark)
        title_label.pack(pady=(2, 8))
        # Scrollable frame for reminders
        frame = ctk.CTkFrame(popup, fg_color="white", corner_radius=14)
        frame.pack(padx=18, pady=4, fill='both', expand=True)
        canvas = ctk.CTkCanvas(frame, bg="white", highlightthickness=0, bd=0, width=340, height=140)
        scrollbar = ctk.CTkScrollbar(frame, orientation="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas, fg_color="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Add reminders
        for rem in reminders:
            frame_row = ctk.CTkFrame(scrollable_frame, fg_color="white")
            frame_row.pack(fill='x', padx=4, pady=2)
            rem_label = ctk.CTkLabel(frame_row, text=rem, font=("Segoe UI", 14), text_color=self.text_dark, anchor="w", justify="left")
            rem_label.pack(side='left', padx=(4, 0), pady=2, fill='x', expand=True)
            # Only show delete button for real reminders
            if rem != "No reminders scheduled.":
                def make_delete_callback(reminder_str):
                    def delete_reminder():
                        # Parse reminder_str to get the name (before ' at ')
                        name = reminder_str.split(' at ')[0]
                        self.scheduler.remove_task(name)
                        # Remove from UI
                        frame_row.destroy()
                    return delete_reminder
                del_btn = ctk.CTkButton(frame_row, text="🗑", width=32, height=28, fg_color=self.accent_dark, hover_color=self.accent, corner_radius=14, font=("Segoe UI", 14), command=make_delete_callback(rem))
                del_btn.pack(side='right', padx=(8, 4))
        # Dismiss button
        dismiss_btn = ctk.CTkButton(popup, text="Dismiss", command=close_popup, corner_radius=18, fg_color=self.accent, hover_color=self.accent_dark, font=("Segoe UI", 14, "bold"))
        dismiss_btn.pack(pady=(12, 8), ipadx=10, ipady=4)
        # Center the popup
        self.after(100, lambda: popup.geometry(f"+{self.winfo_x() + self.winfo_width()//2 - 200}+{self.winfo_y() + self.winfo_height()//2 - 160}"))
        self.attributes('-alpha', 1.0)

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = EmergencySoundTracker()
    app.mainloop()