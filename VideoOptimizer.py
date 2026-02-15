import sys
import os
import re
import threading
import subprocess
from pathlib import Path
from queue import Queue, Empty
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# =================== CONFIG ===================
def detect_ffmpeg():
    import shutil
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    fallback = r"C:\ffmpeg\bin\ffmpeg.exe"
    if os.path.exists(fallback):
        return fallback
    return None

FFMPEG_PATH = detect_ffmpeg()

APP_NAME = "VideoOptimizer"
APP_VERSION = "2.0.1"
APP_AUTHOR = "Mate Technologies"
APP_WEBSITE = "https://matetools.gumroad.com"

SNAPS = [10, 20, 30, 40, 50]

# =================== UTILITY ===================
def win_no_window_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0

def hidden_ffmpeg_startupinfo():
    if sys.platform.startswith("win"):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    return None

def get_video_duration(input_file):
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-i", input_file],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            startupinfo=hidden_ffmpeg_startupinfo(),
            creationflags=win_no_window_flags()
        )
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
        if m:
            h, m_, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h*3600 + m_*60 + s
    except:
        pass
    return None

def estimate_crf(reduction):
    return int(23 + (reduction / 100) * 12)

def calculate_bitrate(target_mb, duration, input_file):
    try:
        input_size = os.path.getsize(input_file)
        target_bytes = input_size * (1 - reduction/100)
        audio_kbps = 128  # audio stays same
        total_kbps = (target_bytes * 8) / duration / 1000  # kbps
        video_kbps = max(100, int(total_kbps - audio_kbps))
        # Ensure we never exceed original bitrate
        orig_kbps = (input_size * 8) / duration / 1000
        return min(video_kbps, int(orig_kbps))
    except:
        return 300  # fallback

def resource_path(name):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return Path(base) / name

# =================== VIDEO CONVERTER CLASS ===================
class VideoConverter:
    def __init__(self, input_file, output_file, reduction, mode, codec="libx264", progress_queue=None):
        self.input_file = input_file
        self.output_file = output_file
        self.reduction = reduction
        self.mode = mode
        self.codec = codec
        self.progress_queue = progress_queue
        self.stop_event = threading.Event()
        self.duration = get_video_duration(input_file)
        self.input_size_mb = os.path.getsize(input_file)/1024/1024

    def stop(self):
        self.stop_event.set()

    def run(self):
        if not self.duration:
            self._send_status("Error: Cannot read video duration")
            return

        target_mb = self.input_size_mb * (1 - self.reduction / 100)

        try:
            if self.mode == "quality":
                # --- Quality Mode (CRF-based) ---
                cmd = [
                    FFMPEG_PATH, "-y", "-i", self.input_file,
                    "-c:v", self.codec,
                    "-preset", "fast",
                    "-crf", str(estimate_crf(self.reduction)),
                    "-c:a", "aac", "-b:a", "128k",
                    self.output_file
                ]
                self._run_ffmpeg(cmd, progress_range=(1, 100))

            else:
                # --- Target Size Mode ---
                # Calculate proper video bitrate
                audio_kbps = 128
                total_bytes = os.path.getsize(self.input_file)
                target_bytes = total_bytes * (1 - self.reduction / 100)
                total_kbps = (target_bytes * 8) / self.duration / 1000  # kbps
                video_kbps = max(100, int(total_kbps - audio_kbps))
                # clamp so it doesn't exceed original bitrate
                orig_kbps = (total_bytes * 8) / self.duration / 1000
                video_kbps = min(video_kbps, int(orig_kbps))

                # --- PASS 1 ---
                pass1_cmd = [
                    FFMPEG_PATH, "-y", "-i", self.input_file,
                    "-c:v", self.codec, "-preset", "fast",
                    "-b:v", f"{video_kbps}k", "-pass", "1",
                    "-an", "-f", "null", "-"
                ]
                self._run_ffmpeg(pass1_cmd, progress_range=(1,50), analyze_only=True)

                # --- PASS 2 ---
                pass2_cmd = [
                    FFMPEG_PATH, "-y", "-i", self.input_file,
                    "-c:v", self.codec, "-preset", "fast",
                    "-b:v", f"{video_kbps}k", "-pass", "2",
                    "-c:a", "aac", "-b:a", "128k",
                    self.output_file
                ]
                self._run_ffmpeg(pass2_cmd, progress_range=(51,100))
                self._cleanup_pass_logs()

            # --- Conversion complete ---
            if os.path.exists(self.output_file):
                out_size = os.path.getsize(self.output_file)/1024/1024
                achieved = 100 - (out_size/self.input_size_mb * 100)
                self._send_status(f"Completed ({achieved:.1f}% reduced)")
            else:
                self._send_status("Completed")

        except Exception as e:
            self._send_status(f"Failed: {e}")

    def _run_ffmpeg(self, cmd, progress_range=(1,100), analyze_only=False):
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1,
                startupinfo=hidden_ffmpeg_startupinfo(),
                creationflags=win_no_window_flags()
            )
        except Exception as e:
            self._send_status(f"FFmpeg error: {e}")
            return

        last_percent = progress_range[0]

        while True:
            raw_line = process.stdout.readline()
            if not raw_line:
                break
            if self.stop_event.is_set():
                process.terminate()
                self._send_status("Stopped")
                return
            try:
                line = raw_line.decode('utf-8', errors='ignore').strip()
            except:
                line = ""

            m = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
            if m and self.duration:
                h, m_, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                cur_time = h*3600 + m_*60 + s
                percent = progress_range[0] + (cur_time/self.duration)*(progress_range[1]-progress_range[0])
                percent = max(1, min(100, percent))  # clamp to 1-100%
                if percent - last_percent >= 0.5:  # smooth updates
                    last_percent = percent
                    self._send_progress(percent)
                    self._send_status(f"{'Analyzing' if analyze_only else 'Converting'}… {percent:.1f}%")

        process.wait()

        if not analyze_only and os.path.exists(self.output_file):
            try:
                out_size = os.path.getsize(self.output_file)/1024/1024
                achieved = 100 - (out_size/self.input_size_mb * 100)
                self._send_status(f"Completed ({achieved:.1f}% reduced)")
            except:
                self._send_status("Completed")

    def _send_progress(self, val):
        if self.progress_queue:
            self.progress_queue.put(('progress', val))

    def _send_status(self, msg):
        if self.progress_queue:
            self.progress_queue.put(('status', msg))

    def _cleanup_pass_logs(self):
        for f in ["ffmpeg2pass-0.log","ffmpeg2pass-0.log.mbtree"]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except: pass

# =================== GUI ===================
# =================== GUI ===================
class VIDConverterApp:
    def __init__(self):
        # ---------------- MAIN WINDOW ----------------
        self.app = tk.Tk()
        self.app.geometry("800x520")
        self.app.title(f"{APP_NAME} {APP_VERSION}")

        # Apply ttkbootstrap style
        self.style = tb.Style(theme="superhero")

        # Optional: set icon
        try:
            self.app.iconbitmap(str(resource_path("logo.ico")))
        except Exception as e:
            print("Icon error:", e)

        # ---------------- VARIABLES ----------------
        self.video_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.reduce_var = tk.IntVar(value=20)
        self.mode_var = tk.StringVar(value="size")
        self.codec_var = tk.StringVar(value="libx264")
        self.progress_val = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Idle")
        self.estimated_size_var = tk.StringVar(value="Estimated size: —")

        self.progress_queue = Queue()
        self.converter = None

        # ---------------- UI ----------------
        self._build_ui()
        self.app.after(100, self._update_ui)

        # ---------------- Drag & Drop ----------------
        try:
            self.app.drop_target_register(tk.DND_FILES)
            self.app.dnd_bind('<<Drop>>', self._on_drop)
        except:
            pass

        # ---------------- MENU ----------------
        menubar = tk.Menu(self.app)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.app.config(menu=menubar)

    # ---------------- BUILD UI ----------------
    def _build_ui(self):
        # Title
        tb.Label(self.app, text=APP_NAME, font=("Segoe UI", 18, "bold")).pack(pady=(10,2))
        tb.Label(self.app, text="Fast, Smart Video Compression & Conversion",
                 font=("Segoe UI",10,"italic"), foreground="#9ca3af").pack(pady=(0,10))

        # Input
        input_frame = tb.Labelframe(self.app, text="Video Input", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)
        tb.Entry(input_frame, textvariable=self.video_path).pack(side="left", fill="x", expand=True, padx=5)
        tb.Button(input_frame, text="Browse", command=self._select_video, bootstyle="info-outline").pack(side="left")

        # Output
        output_frame = tb.Labelframe(self.app, text="Output File", padding=10)
        output_frame.pack(fill="x", padx=10, pady=5)
        tb.Entry(output_frame, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=5)
        tb.Button(output_frame, text="Browse", command=self._select_output, bootstyle="info-outline").pack(side="left")

        # Reduction
        size_frame = tb.Labelframe(self.app, text="Reduce File Size", padding=10)
        size_frame.pack(fill="x", padx=10, pady=5)

        tb.Label(size_frame, text="Reduction:").pack(side="left")
        self.reduction_label = tb.Label(size_frame, text=f"{self.reduce_var.get()}%")
        self.reduction_label.pack(side="right")

        reduction_slider = tb.Scale(size_frame, from_=5, to=80, orient="horizontal",
                                    length=350, variable=self.reduce_var,
                                    command=self._update_reduction)
        reduction_slider.pack(side="left", padx=10)
        reduction_slider.bind("<MouseWheel>", self._wheel_slider)

        tb.Label(size_frame, textvariable=self.estimated_size_var).pack(anchor="w", pady=3)

        # Presets
        preset_frame = tb.Frame(size_frame)
        preset_frame.pack()
        for p in SNAPS:
            tb.Button(preset_frame, text=f"{p}%", command=lambda x=p: self._apply_preset(x), bootstyle="primary").pack(side="left", padx=3)

        # Mode
        mode_frame = tb.Frame(size_frame)
        mode_frame.pack(pady=5)
        tb.Radiobutton(mode_frame, text="Target Size", variable=self.mode_var, value="size").pack(side="left", padx=5)
        tb.Radiobutton(mode_frame, text="Quality Priority", variable=self.mode_var, value="quality").pack(side="left", padx=5)
        tb.OptionMenu(mode_frame, self.codec_var, "", "libx264", "libx265", bootstyle="secondary").pack(side="left", padx=5)

        # Controls
        control = tb.Frame(self.app)
        control.pack(pady=10)
        self.start_btn = tb.Button(control, text="Start ▶", bootstyle="success", command=self._start_conversion)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tb.Button(control, text="Stop", bootstyle="danger", command=self._stop_conversion, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        tb.Label(self.app, textvariable=self.status_var).pack()
        tb.Progressbar(self.app, variable=self.progress_val, maximum=100).pack(fill="x", padx=10, pady=5)

        self.reduce_var.trace_add("write", self._update_estimated_size)

    # ---------------- FILE PICKERS ----------------
    def _select_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files","*.mp4 *.avi *.mov *.mkv")])
        if path:
            self.video_path.set(path)
            self._update_estimated_size()

    def _select_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4","*.mp4"),("MKV","*.mkv")])
        if path:
            self.output_path.set(path)

    # ---------------- UI HELPERS ----------------
    def _apply_preset(self, val):
        self.reduce_var.set(val)
        self.reduction_label.config(text=f"{val}%")
        self._update_estimated_size()

    def _update_reduction(self, val):
        v = int(float(val))
        for s in SNAPS:
            if abs(v - s) <= 2:
                v = s
                self.reduce_var.set(v)
                break
        self.reduction_label.config(text=f"{v}%")
        self._update_estimated_size()

    def _wheel_slider(self, event):
        step = 1 if event.delta>0 else -1
        self.reduce_var.set(max(5,min(80,self.reduce_var.get()+step)))

    def _update_estimated_size(self, *args):
        try:
            if not self.video_path.get():
                self.estimated_size_var.set("Estimated size: —")
                return
            size = os.path.getsize(self.video_path.get())
            reduction = self.reduce_var.get()
            est = size*(1-reduction/100)
            self.estimated_size_var.set(f"Estimated size: {est/1024/1024:.2f} MB")
        except:
            self.estimated_size_var.set("Estimated size: —")

    def _on_drop(self, event):
        path = event.data
        if path.endswith((".mp4",".avi",".mov",".mkv")):
            self.video_path.set(path)
            self._update_estimated_size()

    # ---------------- CONVERSION ----------------
    def _start_conversion(self):
        if not FFMPEG_PATH:
            messagebox.showerror("FFmpeg Missing", "FFmpeg not found. Install or add to PATH.")
            return
        if not self.video_path.get() or not self.output_path.get():
            messagebox.showerror("Error", "Select input and output files.")
            return

        # Disable start, enable stop
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_val.set(1)  # start at 1%
        self.status_var.set("Starting…")

        # Create and start the converter thread
        self.converter = VideoConverter(
            self.video_path.get(),
            self.output_path.get(),
            self.reduce_var.get(),
            self.mode_var.get(),
            codec=self.codec_var.get(),
            progress_queue=self.progress_queue
        )
        threading.Thread(target=self.converter.run, daemon=True).start()

    def _stop_conversion(self):
        if self.converter:
            self.converter.stop()
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        self.status_var.set("Stopping…")

    def _update_ui(self):
        while True:
            try:
                msg_type, val = self.progress_queue.get_nowait()
                if msg_type=="progress":
                    self.progress_val.set(min(100, max(0, val)))
                elif msg_type=="status":
                    self.status_var.set(val)
                    # Re-enable buttons if done
                    if val.startswith("Completed") or val.startswith("Failed") or val=="Stopped":
                        self.start_btn.config(state="normal")
                        self.stop_btn.config(state="disabled")
            except Empty:
                break
        self.app.after(50, self._update_ui)

    # ---------------- ABOUT ----------------
    def _show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            f"{APP_NAME} is a fast, lightweight video converter with smart compression.\n\n"
            "Key Features:\n"
            "• Convert videos to MP4/MKV with smart compression\n"
            "• Quality vs Size mode (CRF or Target Size)\n"
            "• Live estimated output size preview\n"
            "• Adjustable bitrate and CRF for advanced control\n"
            "• Real-time progress bar with stop support\n"
            "• Fully offline processing (no internet required)\n"
            "• Modern UI using ttkbootstrap\n"
            "• Thread-safe background processing\n\n"
            f"{APP_AUTHOR} / Website: {APP_WEBSITE}"
        )

    # ---------------- RUN APP ----------------
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    app = VIDConverterApp()
    app.run()