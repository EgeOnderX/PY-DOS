# PY-DOS V2.0.0-B

PY-DOS is a retro-inspired, terminal-based operating system simulator written entirely in Python. Designed to mimic classic command-line environments like MS-DOS, it offers an expandable, educational platform for experimenting with virtual file systems, memory management, basic CPU cycle tracking, and scripting.

Due to community interest, the project has been updated with an enhanced architecture featuring a Virtual Machine Manager, interactive GUI/terminal execution modes, modular drive mounting, and interactive batch scripting capabilities.

> **Release Note:** This repository contains **PY-DOS v2.0.0-B (Beta)**. While core functionality is completely stable, full version selection within individual virtual machines is still under active development. It is fully recommended and safe to use **v2.0.0-B** as the latest primary release.

---

## What's New in v2.0.0-B

* **VM Manager Interface (`main.py`)**: A Graphical Virtual Machine Manager built using `tkinter` to create, configure, edit, and launch multiple PY-DOS environments seamlessly.
* **Native GUI Terminal & Dual Operating Modes**: Run PY-DOS inside a standalone Tkinter GUI window or directly in your host system's native command prompt/terminal.
* **Interactive Batch Scripting (`.app` engine)**: Enhanced execution pipeline supporting variables (`%VAR%`), custom environment variables, dynamic user prompts (`SET /P`), labels (`:LABEL`), control flow (`GOTO`, `IF`), custom menu rendering (`MENU`), and recursion safeguards.
* **PYIMG Virtual Disk Support**: Mount (`INSERT`) and unmount (`EJECT`) external `.pyimg` virtual floppy/disk files dynamically as extra drives (`A:`, `B:`, etc.) alongside the main `C:` drive.
* **Built-in Mini Text Editor (`EDIT`)**: Integrated text editor supporting file opening, editing, saving, cut/paste operations, and keyboard shortcuts in both terminal and GUI modes.
* **Enhanced Anti-Malware Service (AMS Deluxe)**: Real-time and deep scanning engine detecting malicious command repetitions, loop virus conditions, and dangerous disk operations.

---

## System Requirements

* **Python**: 3.8 or higher
* **Dependencies**: Uses standard Python libraries (`tkinter`, `json`, `os`, `sys`, `subprocess`, `re`, `secrets`, `time`). No third-party packages required.

---

## Installation & Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/EgeOnderX/PY-DOS.git
   cd PY-DOS
   ```

2. **Launch the VM Manager:**
   ```bash
   python main.py
   ```

3. **Create and Run a Virtual Machine:**
   * Click **Create VM**, enter a VM name (e.g., `DefaultVM`), configure memory/disk size, and click **Create**.
   * Select your created VM from the list and click **Start VM**.

4. **Launch directly via Command Line (Bypassing GUI Manager):**
   * Launch in Tkinter GUI Terminal mode:
     ```bash
     python vm.py DefaultVM
     ```
   * Launch directly in system CLI terminal mode:
     ```bash
     python vm.py DefaultVM --terminal
     ```

---

## Technical Specifications & Architecture

* **Virtual Disk System (`disk.py` / `Disk`)**: Uses JSON storage to simulate block allocation and disk drives up to configured capacities (default 512 MB). Disk data persists automatically.
* **Virtual Memory (`RAM`)**: Simulates 128 MB RAM (configurable) tracking key-value allocations with auto-spill and memory clear protections.
* **CPU Simulation (`CPU`)**: Tracks executed operation cycles (`CLEARCPU`, `SYSINFO`).
* **Drive Structure**: Supports multi-drive mapping (`C:` for primary system disk, plus mounted `.pyimg` images).

---

## Scripting & Writing Applications (`.app`)

You can write executable scripts using the built-in `EDIT` command or `WRITE` command. Applications run sequentially and support interactive scripting.

### Script Commands Overview
* `ECHO <text>` / `ECHO OFF` / `ECHO ON`: Output control.
* `SET /P var=Prompt`: Pause execution to ask for user text input.
* `MENU "Title" "Option 1" "Option 2"`: Displays an interactive menu window.
* `GOTO :LABEL` / `:LABEL`: Jump to a specific section inside the script.
* `IF "%var%"=="value" GOTO :LABEL`: Conditional execution.
* `PAUSE`: Wait for user input before proceeding.

### Example Script (`hello.app`)
Create a file named `hello.app` inside PY-DOS using `EDIT hello.app`:

```dos
@ECHO OFF
CLS
ECHO Welcome to PY-DOS Application Engine!
SET /P username=Enter your name: 
ECHO Hello, %username%!
PAUSE
```

Run it directly from the prompt:
```dos
C:\> RUN hello
```
*(Or simply type `hello`)*

---

## Command Reference

| Command | Usage / Description |
| :--- | :--- |
| **`DIR [path]`** | List files and directories in current or targeted folder. |
| **`CD <folder>`** | Change current working directory. |
| **`MKDIR <folder>`** | Create a new directory. |
| **`TREE [path]`** | Display directory structure as a visual tree. |
| **`TYPE <file>`** | Display file contents in the terminal. |
| **`WRITE <file> <text>`** | Quickly write inline text content to a file. |
| **`EDIT [file]`** | Open the interactive Mini Text Editor. |
| **`DEL <file>`** | Delete a specified file. |
| **`COPY <src> <dst>`** | Copy a file from source to destination path. |
| **`RENAME <old> <new>`** | Rename an existing file. |
| **`RUN <app>`** | Execute a `.app` application script. |
| **`INSERT <file.pyimg>`** | Mount an external disk image file. |
| **`EJECT <drive>`** | Unmount a mounted drive letter (e.g., `EJECT A`). |
| **`RAMLOAD <key> <val>`** | Load a temporary key-value pair into RAM. |
| **`RAMSHOW`** | View all current items in virtual RAM memory. |
| **`RAMCLEAR`** | Clear all virtual memory contents. |
| **`SAVE`** | Commit all current RAM states permanently to disk. |
| **`SYSINFO`** | Display complete system information (CPU cycles, RAM, Disk usage). |
| **`AMS`** | View Anti-Malware status report (`AMS /SCAN`, `AMS /ENABLE`, `AMS /DISABLE`). |
| **`FORMAT`** | Format and wipe the active virtual disk. |
| **`REBOOT`** | Commit memory changes and restart the PY-DOS virtual machine. |
| **`CLS` / `CLEAR`** | Clear terminal screen output. |
| **`SHUTDOWN` / `EXIT`** | Shut down and exit PY-DOS. |

---

## License

Starting with version **v2.0.0**, the PY-DOS project has been relicensed from the MIT License to the **Apache License 2.0**.

* **License Transition:** PY-DOS v1.x releases were distributed under the MIT License. Effective with v2.0.0 (and v2.0.0-B), all development and distribution are covered under Apache 2.0.
* For more details and full licensing terms, please refer to the `LICENSE` file in the repository.

---

## Development & Status

* **Current Stable Version**: `v2.0.0-B` (Beta)
* **Maintainer**: Ege Önder
* **License**: MIT License
* **Embedded Hardware Port**: For MicroPython/ESP32 implementations, check out [PY-DOS-on-ESP32](https://github.com/EgeOnderX/PY-DOS-on-ESP32).
