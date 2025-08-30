# This product is no longer supported. Please take a closer look at: https://github.com/EgeOnderX/PY-DOS-on-ESP32
## PY-DOS 1.0.3

**PY-DOS** is a retro-inspired, terminal-based operating system simulation written entirely in Python.

It recreates the classic DOS experience while providing an educational and expandable platform for learning file systems, memory management, and command-line interfaces.

> Developed from scratch by **Ege**  
> Licensed under the **MIT License**

---

## Features

- Virtual RAM and Disk system (`ram.py`, `disk.py`)
- JSON-based disk storage (simulating 512 MB)
- File & folder commands: `MKDIR`, `CD`, `TREE`, `COPY`, `RENAME`, etc.
- CPU and RAM simulation with basic cycle tracking (`cpu.py`, `ram.py`)
- Command-line interface with keyboard input
- Modular and expandable code structure
- **AMS (Anti-Malware Service)** for scanning RAM and Disk
- Application run system (`RUN <file>` command)

---

## What's New?
- Added **helpall** command for more detailed information.
- Introduced a **protection counter** against loop viruses.
- Implemented a new **AMS logging system**.
- Added a lightweight **edit application**.
- **Reduced overall size** through optimizations.
- Added real time protection.

---

## Technical Details

- PY-DOS uses a **128 MB RAM simulation** and a **512 MB virtual disk** (`disk.json`)
- The disk is JSON-based and saves automatically after a **REBOOT**
- Use `RAMLOAD` for temporary RAM storage; commit to disk with `REBOOT`
- Anti-Malware Service scans for suspicious content, e.g., `format` commands
- All data is saved between sessions through `disk.json`
- Cross-platform: Works on Windows, Linux, and macOS
- Removed the requirement to define separate commands for both run and cmd.

---


## How to Write Your Own Program in PY-DOS

In PY-DOS, you can write simple applications directly in the terminal using the `WRITE` command.  
The format is:

write <filename> utf8 <your code here>
- `<filename>`: Name of your application file.  
- `utf8`: Indicates the file contains executable terminal code.  
- `<your code here>`: The commands your application will execute when run.

### Example

write myapp utf8 print Hello, World!; print Welcome to PY-DOS

- This creates a file called `myapp`.  
- When you run it with `RUN myapp`, it will execute the commands:

'print Hello, World!'
'print Welcome to PY-DOS'


### Running Your Application

'run myapp'

### NOTES
- The terminal executes all commands in sequence.  
- You can include multiple commands separated by semicolons (`;`).  
- Supported commands are the same as in the terminal, e.g., `PRINT`, `WRITE`, `DEL`, `REBOOT`, etc.

---

## Requirements

- Python 3.8 or later

---

## Screenshots


# Run program system


<img width="1091" height="513" alt="image" src="https://github.com/user-attachments/assets/02bec0f9-9672-4386-9341-cd02065e3244" />


---

# AMS


<img width="932" height="556" alt="image" src="https://github.com/user-attachments/assets/a2fb124d-ccda-4b75-922f-1336d95c0cd1" />


---


# AMS


<img width="751" height="439" alt="image" src="https://github.com/user-attachments/assets/b5405ae0-85c4-4f1d-84ce-2c15c82b0368" />


---


# Pony Virus Testing 7 fps ( https://github.com/EgeOnderX/PY-DOS-App-Pack/blob/main/viruses/pony/pony.txt )


![ams](https://github.com/user-attachments/assets/f7270000-b451-492b-86d0-e32148216ee3)



---

## All Commands

- DIR - List files and directories  
- TREE - Display directory tree  
- TYPE <file> - Show file content  
- WRITE <file> <txt> - Write text to a file (RAM+Disk)  
- DEL <file> - Delete a file from RAM and Disk  
- RENAME <old> <new> - Rename a file  
- COPY <src> <dst> - Copy a file  
- MKDIR <folder> - Create a new directory  
- CD <folder> / CCD - Change current directory  
- RUN <file> - Run a script or application  
- SAVE - Save RAM contents to Disk  
- RAMLOAD <key> <value> - Load a key-value into RAM  
- RAMCLEAR - Clear all RAM contents  
- RAMSHOW - Display RAM contents  
- SYSINFO - Display system information  
- REBOOT - Save RAM to disk and reboot the system  
- FORMAT - Format (reset) the disk  
- PRINT <text> - Print text to screen  
- CLEARCPU - Reset CPU cycles to 0  
- AMS - Run Anti-Malware Scan (RAM & Disk)  
- HELP - Display all available commands  
- EXIT - Exit PY-DOS
