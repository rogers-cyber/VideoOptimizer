# VideoOptimizer v2.0.1 – Fast & Smart Video Conversion Tool (Source Code + EXE)

VideoOptimizer v2.0.1 is a professional, high-performance desktop application for converting and compressing video files.  
It is designed for speed, efficiency, and simplicity, with smart compression modes, real-time progress, and estimated output size previews.

This repository includes:
- Full Python source code
- Prebuilt Windows executable available under the Releases section
- Portable desktop utility for daily and professional video workflows

------------------------------------------------------------
WINDOWS DOWNLOAD (EXE)
------------------------------------------------------------

Download the latest Windows executable from GitHub Releases:

https://github.com/rogers-cyber/VideoOptimizer/releases

- No Python required
- Portable executable
- Ready-to-run on Windows

------------------------------------------------------------
FEATURES
------------------------------------------------------------

- Convert Videos — MP4 / MKV output
- Smart Compression — Reduce file size without noticeable quality loss
- Two Modes:
  - **Target Size Mode** — Reduce file to a target percentage of original
  - **Quality Priority Mode** — Control CRF for consistent visual quality
- Adjustable Bitrate & Codec
  - H.264 (libx264)
  - H.265 (libx265)
- Real-Time Progress Bar
  - Percent complete
  - Status messages
- Live Estimated Output Size Preview
- Preset Reduction Options (10%, 20%, 30%, 40%, 50%)
- Drag & Drop Support for video files
- Threaded Background Conversion — UI remains responsive
- Stop / Resume Conversion
- Fully Offline Processing (no internet required)
- Modern UI using ttkbootstrap
- Cross-platform Python source (Windows EXE provided)

------------------------------------------------------------
SUPPORTED VIDEO FORMATS
------------------------------------------------------------

- MP4 (.mp4)  
- AVI (.avi)  
- MOV (.mov)  
- MKV (.mkv)  

------------------------------------------------------------
REPOSITORY STRUCTURE
------------------------------------------------------------

VideoOptimizer/
├── VIDConverter-Pro.py
├── dist/
│   └── (empty or .gitkeep)
├── logo.ico
├── requirements.txt
├── README.md
└── LICENSE

------------------------------------------------------------
INSTALLATION (SOURCE CODE)
------------------------------------------------------------

1. Clone the repository:

```
git clone https://github.com/yourusername/VideoOptimizer.git
cd VideoOptimizer
```

2. Install dependencies:

```
pip install -r requirements.txt
```

(Tkinter is included with standard Python installations.)

3. Run the application:

```
python VIDConverter-Pro.py
```

------------------------------------------------------------
HOW TO USE
------------------------------------------------------------

1. **Select Input Video**
   - Click "Browse" or drag & drop your video file

2. **Select Output File**
   - Choose output location and filename

3. **Set Reduction**
   - Use slider or presets (10–50%)
   - Select mode: Target Size or Quality Priority
   - Optional: Choose codec (libx264 / libx265)

4. **Start Conversion**
   - Click "Start ▶"
   - Monitor progress and status updates

5. **Stop Conversion**
   - Click "Stop" to cancel any ongoing process

6. **Review Output**
   - Check final file size and achieved compression

------------------------------------------------------------
DEPENDENCIES
------------------------------------------------------------

- Python 3.9+
- ttkbootstrap
- Tkinter
- threading / subprocess / re / os / sys / pathlib / queue (standard Python libraries)
- FFmpeg (must be installed or included in PATH)

See requirements.txt for exact versions.

------------------------------------------------------------
NOTES
------------------------------------------------------------

- Estimated size is calculated based on reduction percentage
- Quality Mode uses CRF to maintain visual fidelity
- Target Size Mode performs 2-pass encoding for better bitrate control
- Conversion progress is updated in real-time
- Performance depends on video duration, resolution, and disk speed

------------------------------------------------------------
ABOUT
------------------------------------------------------------

VideoOptimizer is a lightweight, fast desktop utility created for smart video compression and format conversion.  

It is suitable for:
- Video editors
- Content creators
- Developers needing automated video workflows
- Power users handling large video collections

------------------------------------------------------------
LICENSE
------------------------------------------------------------

This project is licensed under the MIT License.

You are free to use, modify, and distribute this software,  
including the source code and compiled executable, with attribution.

See the LICENSE file for full details.
