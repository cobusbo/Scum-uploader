# SCUM ServerSettings Scheduled Uploader

🛠️ A powerful desktop app to **automate uploading of `ServerSettings.ini`** files to your SCUM server using **FTP** or **SFTP**. Easily manage and schedule different configuration files (called _namesets_) for upload based on server restart cycles.

> ✅ Designed for Windows  
> ✅ No need to use a console  
> ✅ Useful for automatically swapping settings like **loot**, **mechs**, **weather**, or **PvP rules** throughout the day

---

## 🚀 Features

- 🔁 Uploads `ServerSettings.ini` at scheduled intervals
- 📁 Assign different `.ini` config files (namesets) for each scheduled time
- ⏱ Specify how many seconds *before restart* to upload
- 🖱 Manual upload trigger with one click
- 🔐 Supports **FTP** and **SFTP** (via `paramiko`)
- 🔔 Optional Windows notifications (via `win10toast`)
- 💾 Saves all settings in `scum_uploader_settings.json`
- 📝 Live activity log with timestamps
- ✅ Fully GUI-based — no coding or console required!

---

## 🖼️ Interface Preview

> *(Add a screenshot if desired and link to it like `![UI](docs/screenshot.png)`)*

---

## 🧰 Requirements

- Python **3.8+**
- [`paramiko`](https://pypi.org/project/paramiko/) – SFTP support  
- [`win10toast`](https://pypi.org/project/win10toast/) – Windows notifications (optional)
- `tkinter` – GUI toolkit (included with most Python installations)

### 📦 Install dependencies:

```bash
pip install paramiko win10toast
```
📂 Folder Structure
```
Scum-uploader/
├── SettingsNamesets/              # Place your .ini files here
│   ├── PvE_Day.ini
│   ├── PvP_Night.ini
│   └── ...
├── scum_uploader.py               # Main script
├── scum_uploader_settings.json    # Auto-generated settings file
└── README.md
🔧 Usage Instructions
🎯 Launch scum_uploader.py using Python or run the EXE if compiled.

🔐 Fill in your FTP or SFTP connection details.

📅 Choose how often uploads should occur (e.g., every 6 hours).

⏳ Set how many seconds before restart to upload the file.

📁 Assign a .ini file (nameset) for each scheduled upload time.

💾 Click Save Settings.

🟢 Keep the app running — it will handle uploads in the background automatically.

🖱 Use the Manual Upload button any time you want to override the schedule.

🏗️ Creating a Standalone EXE (Optional)
Use PyInstaller to package the app:
```
```
pip install pyinstaller


pyinstaller --noconsole --onefile ^
  --add-data "SettingsNamesets;SettingsNamesets" ^
  scum_uploader.py
```
Then copy the generated .exe (in the dist/ folder) next to your SettingsNamesets folder.

❓ FAQ
```
Q: Can I use this on Linux or macOS?
A: The Python script works on all platforms, but toast notifications are Windows-only. You may need to modify file paths or notification logic for other OSes.

Q: What should I name my config files?
A: Any valid .ini file placed in SettingsNamesets/ will appear in the dropdown menus for scheduling.

Q: Will it always upload to ServerSettings.ini?
A: Yes — the tool uploads your selected .ini file and renames it to ServerSettings.ini on the server.
```
🧑‍💻 Developer
```cobusbo
📍 South Africa
🎮 SCUM server admin & developer
💬 Contact via GitHub Issues
```

📄 License
This project is open source under the MIT License.
See LICENSE for details.
