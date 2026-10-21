# 🐍 Python Scripts for Windows

A collection of Python utilities designed to simplify everyday Windows tasks, including file management, application launching, system monitoring, and process inspection.

## Features

- **APEX File System Controller** — Find, open, list, search, and organize files using natural-language commands.
- **Application Launcher** — Launch applications, open websites, and search the web through Google Chrome.
- **System Monitor** — Monitor CPU, RAM, and disk usage with desktop notifications and logs.
- **Process Manager** — Inspect running processes and view their CPU and memory usage.
- **Typo-Tolerant Search** — Find files and applications even when their names are misspelled.

## Project Structure

```text
Python-Scripts-For-Windows/
├── files.py
├── main.py
├── open_program.py
├── system_info.py
└── system_processes.py
```

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or later
- pip

## Installation

Clone the repository:

```bash
git clone https://github.com/arnavafk12-ship-it/Python-Scripts-For-Windows.git
cd Python-Scripts-For-Windows
```

Install the dependencies:

```bash
pip install rapidfuzz psutil plyer pywin32
```

For the file controller's Recycle Bin functionality, install:

```bash
pip install send2trash
```

## Usage

### 1. APEX File System Controller

Run:

```bash
python files.py
```

Example commands:

```text
open downloads
find docker
list downloads
count downloads
size downloads
largest files in C:\
search *.py
tree downloads
drives
help
exit
```

The controller supports natural-language commands and typo-tolerant file discovery. File-changing operations ask for confirmation.

### 2. Application Launcher

Run:

```bash
python open_program.py
```

Examples:

```text
notepad
google.com
python tutorial -g
exit
```

Enter an application name or website to launch it. Append `-g` to perform a web search.

### 3. System Monitor

Run:

```bash
python system_info.py
```

Default alert thresholds:

| Resource | Threshold |
|---|---:|
| CPU usage | 80% |
| RAM usage | 85% |
| C: drive usage | 90% |

The monitor checks resource usage every 5 seconds and applies a 5-minute cooldown between repeated alerts for each resource.

Logs are saved to `system_monitor_log.txt` on the Desktop.

Press `Ctrl+C` to stop monitoring.

### 4. Process Manager

Run:

```bash
python system_processes.py
```

Displays up to 30 running processes, sorted by RAM usage, including their process IDs, names, CPU usage, and memory usage.

## Safety and Limitations

- Designed for Windows.
- Review file paths carefully before confirming file operations.
- Deletion requires `send2trash` and attempts to move items to the Recycle Bin.
- Some system processes may be inaccessible due to Windows permissions.
- System alerts notify you of resource usage but do not automatically fix performance problems.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

1. Fork this repository.
2. Create a feature branch.
3. Make and test your changes.
4. Submit a pull request describing your improvements.

---

**Built with Python for Windows productivity.**
