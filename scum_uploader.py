import os
import ftplib
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from datetime import datetime, timedelta
import json
import platform
import subprocess

# Import paramiko for SFTP
try:
    import paramiko
except ImportError:
    paramiko = None

# Attempt to import win10toast for Windows notifications
try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
except ImportError:
    toaster = None

SETTINGS_FILE = "scum_uploader_settings.json"
NAMESETS_FOLDER = "SettingsNamesets"
MAX_RETRIES = 3
RETRY_DELAY = 5

class SCUMUploaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SCUM ServerSettings Scheduled Uploader")
        self.geometry("750x650")
        self.minsize(600, 550)
        self.resizable(True, True)

        self.namesets = []

        # FTP/SFTP connection info
        self.protocol_var = tk.StringVar(value="FTP")
        self.ftp_host_var = tk.StringVar()
        self.ftp_port_var = tk.StringVar(value="21")  # Default FTP port
        self.ftp_user_var = tk.StringVar()
        self.ftp_pass_var = tk.StringVar()
        self.ftp_path_var = tk.StringVar(value="/")

        self.interval_var = tk.IntVar(value=6)
        self.before_upload_seconds_var = tk.IntVar(value=120)

        self.schedule_vars = []

        self.load_settings()
        self.load_namesets()

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.create_widgets()

        # Developer label footer
        footer = ttk.Frame(self)
        footer.pack(pady=(0, 10))
        ttk.Label(footer, text="Developed by ", font=("Arial", 9)).pack(side="left")
        ttk.Label(footer, text="cobusbo", font=("Arial", 9, "bold")).pack(side="left")

        self.stop_thread = False
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        # Start the countdown update loop
        self.update_countdown()

    def log(self, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"{timestamp} - {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        print(f"{timestamp} - {msg}")  # Also print to console

    def notify(self, title, message):
        if toaster:
            toaster.show_toast(title, message, duration=5, threaded=True)
        else:
            print(f"Notification: {title} - {message}")

    def create_widgets(self):
        frm_proto = ttk.LabelFrame(self.scrollable_frame, text="Protocol Selection")
        frm_proto.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frm_proto, text="Select Protocol:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        proto_combo = ttk.Combobox(frm_proto, textvariable=self.protocol_var, values=["FTP", "SFTP"], state="readonly", width=10)
        proto_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        frm_ftp = ttk.LabelFrame(self.scrollable_frame, text="Connection Settings")
        frm_ftp.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frm_ftp, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.host_entry = ttk.Entry(frm_ftp, textvariable=self.ftp_host_var, width=25)
        self.host_entry.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(frm_ftp, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.port_entry = ttk.Entry(frm_ftp, textvariable=self.ftp_port_var, width=6)
        self.port_entry.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(frm_ftp, text="Username:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.user_entry = ttk.Entry(frm_ftp, textvariable=self.ftp_user_var, width=35)
        self.user_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=3, sticky=tk.W)

        ttk.Label(frm_ftp, text="Password:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.pass_entry = ttk.Entry(frm_ftp, textvariable=self.ftp_pass_var, show="*", width=35)
        self.pass_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=3, sticky=tk.W)

        ttk.Label(frm_ftp, text="Remote Path:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.path_entry = ttk.Entry(frm_ftp, textvariable=self.ftp_path_var, width=35)
        self.path_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=3, sticky=tk.W)

        frm_sched = ttk.LabelFrame(self.scrollable_frame, text="Upload Schedule Settings")
        frm_sched.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frm_sched, text="Upload Interval (hours):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        interval_entry = ttk.Entry(frm_sched, textvariable=self.interval_var, width=5)
        interval_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        interval_entry.bind("<FocusOut>", lambda e: self.on_interval_change())

        ttk.Label(frm_sched, text="Seconds Before Restart to Upload:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(frm_sched, textvariable=self.before_upload_seconds_var, width=5).grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        self.frm_timeslots = ttk.LabelFrame(self.scrollable_frame, text="Nameset Assignments Per Upload Time")
        self.frm_timeslots.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.update_schedule_dropdowns()

        btn_frame = tk.Frame(self.scrollable_frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Save Settings", command=self.save_settings).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Refresh Namesets", command=self.refresh_namesets).grid(row=0, column=1, padx=10)
        ttk.Button(btn_frame, text="Manual Upload...", command=self.manual_upload_dialog).grid(row=0, column=2, padx=10)

        self.log_text = tk.Text(self.scrollable_frame, height=10, width=85, state="disabled")
        self.log_text.pack(padx=10, pady=10)

        # Countdown label
        self.countdown_var = tk.StringVar(value="Next upload in: --:--:--")
        self.countdown_label = ttk.Label(self.scrollable_frame, textvariable=self.countdown_var, font=("Arial", 12, "bold"))
        self.countdown_label.pack(pady=(0, 10))

    def load_namesets(self):
        if not os.path.exists(NAMESETS_FOLDER):
            os.makedirs(NAMESETS_FOLDER)
        self.namesets = [f for f in os.listdir(NAMESETS_FOLDER) if f.lower().endswith(".ini")]

    def refresh_namesets(self):
        self.load_namesets()
        self.update_schedule_dropdowns()
        self.log(f"Namesets refreshed: {len(self.namesets)} found.")

    def update_schedule_dropdowns(self):
        for widget in self.frm_timeslots.winfo_children():
            widget.destroy()

        interval = self.interval_var.get()
        if interval <= 0 or 24 % interval != 0:
            self.log("Invalid interval: must be a divisor of 24.")
            return

        slots = 24 // interval
        self.schedule_vars.clear()

        ttk.Label(self.frm_timeslots, text="Upload Time", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(self.frm_timeslots, text="Nameset to Upload", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=10, pady=5)

        for i in range(slots):
            hour = (i * interval) % 24
            time_str = f"{hour:02d}:00"
            ttk.Label(self.frm_timeslots, text=time_str).grid(row=i+1, column=0, padx=10, pady=3, sticky=tk.W)

            var = tk.StringVar()
            default_value = self.namesets[0] if self.namesets else ""
            if len(self.schedule_vars) > i:
                default_value = self.schedule_vars[i].get()
            var.set(default_value)

            cb = ttk.Combobox(self.frm_timeslots, textvariable=var, values=self.namesets, state="readonly", width=50)
            cb.grid(row=i+1, column=1, padx=10, pady=3)
            self.schedule_vars.append(var)

    def on_interval_change(self):
        try:
            interval = int(self.interval_var.get())
            if 24 % interval != 0:
                messagebox.showwarning("Warning", "Interval should be a divisor of 24.")
            self.update_schedule_dropdowns()
        except Exception:
            pass

    def save_settings(self):
        settings = {
            "protocol": self.protocol_var.get(),
            "ftp_host": self.ftp_host_var.get(),
            "ftp_port": self.ftp_port_var.get(),
            "ftp_user": self.ftp_user_var.get(),
            "ftp_pass": self.ftp_pass_var.get(),
            "ftp_path": self.ftp_path_var.get(),
            "interval_hours": self.interval_var.get(),
            "before_upload_seconds": self.before_upload_seconds_var.get(),
            "schedule": [var.get() for var in self.schedule_vars],
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
            self.log("Settings saved.")
        except Exception as e:
            self.log(f"Failed to save settings: {e}")

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            self.protocol_var.set(settings.get("protocol", "FTP"))
            self.ftp_host_var.set(settings.get("ftp_host", ""))
            self.ftp_port_var.set(settings.get("ftp_port", "21"))
            self.ftp_user_var.set(settings.get("ftp_user", ""))
            self.ftp_pass_var.set(settings.get("ftp_pass", ""))
            self.ftp_path_var.set(settings.get("ftp_path", "/"))
            schedule_list = settings.get("schedule", [])
            self.schedule_vars = [tk.StringVar(value=name) for name in schedule_list]
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def upload_file_ftp(self, local_path):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.log(f"Connecting to FTP server {self.ftp_host_var.get()} on port {self.ftp_port_var.get()} (Attempt {attempt})...")
                ftp = ftplib.FTP()
                ftp.connect(self.ftp_host_var.get(), int(self.ftp_port_var.get()), timeout=10)
                ftp.login(self.ftp_user_var.get(), self.ftp_pass_var.get())
                ftp.cwd(self.ftp_path_var.get())
                with open(local_path, 'rb') as file:
                    self.log(f"Uploading '{os.path.basename(local_path)}' as 'ServerSettings.ini' ...")
                    ftp.storbinary('STOR ServerSettings.ini', file)
                ftp.quit()
                self.log("Upload successful.")
                self.notify("SCUM Uploader", f"Upload succeeded: {os.path.basename(local_path)}")
                return True
            except Exception as e:
                self.log(f"FTP upload failed (Attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    self.log(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    self.notify("SCUM Uploader", f"Upload failed after {MAX_RETRIES} attempts.")
        return False

    def upload_file_sftp(self, local_path):
        if paramiko is None:
            self.log("Paramiko module not installed. Please install with 'pip install paramiko'.")
            self.notify("SCUM Uploader", "Paramiko not installed. SFTP upload unavailable.")
            return False

        host = self.ftp_host_var.get()
        try:
            port = int(self.ftp_port_var.get())
        except Exception:
            port = 22
        user = self.ftp_user_var.get()
        passwd = self.ftp_pass_var.get()
        remote_path = self.ftp_path_var.get()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.log(f"Connecting to SFTP server {host}:{port} (Attempt {attempt})...")
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Accept unknown keys automatically
                client.connect(hostname=host, port=port, username=user, password=passwd, timeout=10)

                sftp = client.open_sftp()
                remote_file = remote_path.rstrip('/') + '/ServerSettings.ini'
                self.log(f"Uploading '{os.path.basename(local_path)}' to '{remote_file}' ...")
                sftp.put(local_path, remote_file)
                sftp.close()
                client.close()

                self.log("SFTP upload successful.")
                self.notify("SCUM Uploader", f"SFTP Upload succeeded: {os.path.basename(local_path)}")
                return True
            except Exception as e:
                self.log(f"SFTP upload failed (Attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    self.log(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    self.notify("SCUM Uploader", f"SFTP Upload failed after {MAX_RETRIES} attempts.")
        return False

    def manual_upload_dialog(self):
        if not self.namesets:
            messagebox.showerror("Error", "No namesets available to upload.")
            return
        selected = simpledialog.askstring("Manual Upload", f"Enter nameset to upload (Available: {', '.join(self.namesets)})")
        if not selected:
            return
        if selected not in self.namesets:
            messagebox.showerror("Error", f"Nameset '{selected}' not found.")
            return
        local_path = os.path.join(NAMESETS_FOLDER, selected)
        if not os.path.exists(local_path):
            messagebox.showerror("Error", f"File '{selected}' not found.")
            return
        self.log(f"Manual upload of '{selected}' started...")

        threading.Thread(target=self.upload_dispatcher, args=(local_path,), daemon=True).start()

    def upload_dispatcher(self, local_path):
        protocol = self.protocol_var.get()
        if protocol == "FTP":
            self.upload_file_ftp(local_path)
        elif protocol == "SFTP":
            self.upload_file_sftp(local_path)
        else:
            self.log(f"Unknown protocol selected: {protocol}")

    def scheduler_loop(self):
        while not self.stop_thread:
            now = datetime.now()
            interval = self.interval_var.get()
            if interval <= 0 or 24 % interval != 0:
                self.log("Invalid interval, scheduler paused.")
                time.sleep(60)
                continue
            # Calculate next scheduled times
            next_times = [(datetime(now.year, now.month, now.day, (h * interval) % 24, 0, 0)) for h in range(24 // interval)]
            # find next upload time that is in future
            future_times = [t for t in next_times if t > now]
            next_upload_time = future_times[0] if future_times else next_times[0] + timedelta(days=1)

            wait_seconds = (next_upload_time - now).total_seconds() - self.before_upload_seconds_var.get()
            if wait_seconds < 0:
                wait_seconds = 0

            self.log(f"Next upload scheduled at {next_upload_time.strftime('%H:%M:%S')}, waiting {int(wait_seconds)} seconds.")

            # Sleep until before_upload_seconds before upload time
            while wait_seconds > 0 and not self.stop_thread:
                sleep_time = min(10, wait_seconds)
                time.sleep(sleep_time)
                wait_seconds -= sleep_time

            if self.stop_thread:
                break

            # Upload the assigned nameset
            slot_index = next_times.index(next_upload_time if next_upload_time in next_times else next_times[0])
            if slot_index >= len(self.schedule_vars):
                self.log("No nameset assigned for this upload time.")
                time.sleep(60)
                continue
            nameset_name = self.schedule_vars[slot_index].get()
            if not nameset_name:
                self.log("No nameset assigned for this upload time.")
                time.sleep(60)
                continue

            local_path = os.path.join(NAMESETS_FOLDER, nameset_name)
            if not os.path.exists(local_path):
                self.log(f"Nameset file not found: {nameset_name}")
                time.sleep(60)
                continue

            self.log(f"Scheduled upload starting for '{nameset_name}' ...")
            self.upload_dispatcher(local_path)

            # Sleep until after the upload time passed to avoid multiple uploads in one cycle
            time.sleep(60)

    def update_countdown(self):
        if self.stop_thread:
            return

        now = datetime.now()
        interval = self.interval_var.get()
        before_sec = self.before_upload_seconds_var.get()

        if interval <= 0 or 24 % interval != 0:
            self.countdown_var.set("Invalid interval")
        else:
            next_times = [datetime(now.year, now.month, now.day, (h * interval) % 24, 0, 0) for h in range(24 // interval)]
            future_times = [t for t in next_times if t > now]
            next_upload_time = future_times[0] if future_times else next_times[0] + timedelta(days=1)

            upload_start_time = next_upload_time - timedelta(seconds=before_sec)
            if upload_start_time < now:
                self.countdown_var.set("Uploading now or waiting...")
            else:
                diff = upload_start_time - now
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.countdown_var.set(f"Next upload in: {hours:02d}:{minutes:02d}:{seconds:02d}")

        # schedule to run again after 1 second
        self.after(1000, self.update_countdown)

    def on_close(self):
        self.stop_thread = True
        self.scheduler_thread.join(timeout=2)
        self.destroy()


if __name__ == "__main__":
    if platform.system() == "Windows" and toaster is None:
        print("For Windows notifications, install 'win10toast': pip install win10toast")
    if paramiko is None:
        print("Paramiko module not found. Install with: pip install paramiko")

    app = SCUMUploaderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
