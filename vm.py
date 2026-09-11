import json
import os
import re
import secrets
import string
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VMS_DIR = os.path.join(BASE_DIR, "vms")


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_case_insensitive(directory, filename):
    target = filename.casefold()
    if not os.path.isdir(directory):
        return None
    for entry in os.listdir(directory):
        if entry.casefold() == target:
            return os.path.join(directory, entry)
    return None


def random_folder_name(length=12):
    alphabet = string.ascii_lowercase + string.digits
    return "SYS_" + "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_path(path):
    parts = []
    for p in path.replace("\\", "/").split("/"):
        if not p or p == ".":
            continue
        if p == "..":
            if parts:
                parts.pop()
            continue
        parts.append(p)
    return "/" + "/".join(parts)


def disk_value_size(value):
    if isinstance(value, dict):
        return sum(len(str(k).encode("utf-8")) + disk_value_size(v) for k, v in value.items())
    if isinstance(value, list):
        return sum(disk_value_size(v) for v in value)
    return len(str(value).encode("utf-8"))


class Disk:
    def __init__(self, filename, max_size_kb=512 * 1024, create=True):
        self.filename = filename
        self.max_size_kb = int(max_size_kb)
        if create and not os.path.isfile(self.filename):
            self.format_disk()

    def format_disk(self):
        write_json(self.filename, {
            "__disk__": {
                "format": "pydos",
                "version": 1,
                "capacity_kb": self.max_size_kb
            }
        })

    def _load(self):
        data = read_json(self.filename, {})
        return data if isinstance(data, dict) else {}

    def _save(self, data):
        write_json(self.filename, data)

    def _split_path(self, path):
        return [p for p in path.strip("/").split("/") if p]

    def _navigate(self, data, path_parts, create_missing=False):
        for part in path_parts:
            actual = next((k for k in data.keys() if k.casefold() == part.casefold()), None)
            if actual is None:
                if not create_missing:
                    return None
                data[part] = {}
                actual = part
            if not isinstance(data[actual], dict):
                return None
            data = data[actual]
        return data

    def _lookup_key(self, mapping, key):
        for existing in mapping.keys():
            if existing.casefold() == key.casefold():
                return existing
        return None

    def write_file(self, filepath, content):
        data = self._load()
        path_parts = self._split_path(filepath)
        if not path_parts:
            return False
        parent = self._navigate(data, path_parts[:-1], create_missing=True)
        if parent is None:
            return False
        existing = self._lookup_key(parent, path_parts[-1])
        target_name = existing if existing is not None else path_parts[-1]
        old_value = parent.get(target_name)
        parent[target_name] = str(content)

        if self._get_used_space_kb(data) <= self.max_size_kb:
            self._save(data)
            return True

        if existing is None:
            parent.pop(target_name, None)
        else:
            parent[target_name] = old_value
        return False

    def read_file(self, filepath):
        data = self._load()
        path_parts = self._split_path(filepath)
        if not path_parts:
            return "[File not found]"

        current = data
        for part in path_parts[:-1]:
            key = self._lookup_key(current, part)
            if key is None or not isinstance(current[key], dict):
                return "[File not found]"
            current = current[key]

        last = self._lookup_key(current, path_parts[-1])
        if last is None:
            return "[File not found]"
        if isinstance(current[last], dict):
            return "[Is a directory]"
        return str(current[last])

    def delete_file(self, filepath):
        data = self._load()
        parts = self._split_path(filepath)
        if not parts:
            return False

        parent = self._navigate(data, parts[:-1], create_missing=False)
        if parent is None:
            return False

        key = self._lookup_key(parent, parts[-1])
        if key is None or isinstance(parent[key], dict):
            return False

        del parent[key]
        self._save(data)
        return True

    def mkdir(self, folder_path):
        data = self._load()
        parts = self._split_path(folder_path)
        if not parts:
            return False

        parent = self._navigate(data, parts[:-1], create_missing=True)
        if parent is None:
            return False

        existing = self._lookup_key(parent, parts[-1])
        if existing is not None:
            return False

        parent[parts[-1]] = {}
        if self._get_used_space_kb(data) <= self.max_size_kb:
            self._save(data)
            return True

        del parent[parts[-1]]
        return False

    def list_dir(self, folder_path):
        data = self._load()
        parts = self._split_path(folder_path)
        current = data

        for part in parts:
            key = self._lookup_key(current, part)
            if key is None or not isinstance(current[key], dict):
                return []
            current = current[key]

        return [k for k in current.keys() if k != "__disk__"]

    def is_folder(self, path):
        if normalize_path(path) == "/":
            return True

        data = self._load()
        parts = self._split_path(path)
        current = data

        for i, part in enumerate(parts):
            key = self._lookup_key(current, part)
            if key is None:
                return False

            if i == len(parts) - 1:
                return isinstance(current[key], dict)

            if not isinstance(current[key], dict):
                return False

            current = current[key]

        return True

    def _get_used_space_kb(self, data=None):
        data = self._load() if data is None else data
        return disk_value_size(data) // 1024

    def get_info(self):
        data = self._load()
        used = self._get_used_space_kb(data)
        return {
            "max_kb": self.max_size_kb,
            "used_kb": used,
            "free_kb": max(0, self.max_size_kb - used),
            "file_count": self._count_files(data)
        }

    def _count_files(self, value):
        if isinstance(value, dict):
            return sum(self._count_files(v) for k, v in value.items() if k != "__disk__")
        return 1

    def get_structure(self):
        return self._load()

    def write_bulk(self, data_dict):
        for filepath, content in data_dict.items():
            self.write_file(filepath, content)


class RAM:
    def __init__(self, size_kb=128 * 1024):
        self.size_kb = int(size_kb)
        self.memory = {}

    def _used_bytes(self):
        total = 0
        for k, v in self.memory.items():
            total += len(str(k).encode("utf-8"))
            total += len(str(v).encode("utf-8"))
        return total

    def load(self, key, value):
        old = self.memory.get(key)
        self.memory[key] = value

        if self._used_bytes() > self.size_kb * 1024:
            if old is None:
                self.memory.pop(key, None)
            else:
                self.memory[key] = old
            return False
        return True

    def get(self, key):
        if key in self.memory:
            return self.memory[key]
        for existing, value in self.memory.items():
            if existing.casefold() == key.casefold():
                return value
        return None

    def pop(self, key, default=None):
        if key in self.memory:
            return self.memory.pop(key)
        for existing in list(self.memory.keys()):
            if existing.casefold() == key.casefold():
                return self.memory.pop(existing)
        return default

    def clear(self):
        self.memory = {}

    def get_info(self):
        used = self._used_bytes()
        total = self.size_kb * 1024
        return {
            "total_kb": self.size_kb,
            "used_kb": used // 1024,
            "free_kb": max(0, (total - used) // 1024)
        }


class CPU:
    def __init__(self):
        self.cycles = 0

    def execute(self, command):
        self.cycles += 1
        return command.strip().split()

    def get_info(self):
        return {"cycles": self.cycles}

    def clearcpu(self):
        self.cycles = 0


class AntiMalware:
    def __init__(self, vm):
        self.vm = vm
        self.command_history = {}
        self.enabled = True

    def record_command(self, cmd):
        if not self.enabled:
            return
        cmd_lower = cmd.lower()
        self.command_history[cmd_lower] = self.command_history.get(cmd_lower, 0) + 1
        count = self.command_history[cmd_lower]

        if count > 500:
            self._log(f"ALERT: Command repetition threshold reached for: {cmd_lower}")

    def _log(self, text):
        disk = self.vm.drives.get("C", self.vm.disk)
        if not disk.is_folder("/ams"):
            disk.mkdir("/ams")
        disk.write_file("/ams/amslog.txt", text)

    def scan(self, silent=False, delete=False):
        if not silent:
            self.vm.print_output("=== Anti-Malware Service Deluxe ===")
            self.vm.print_output("Scanning system...")

        suspicious_found = False

        for key in list(self.vm.ram.memory.keys()):
            value = str(self.vm.ram.memory[key])

            if "format" in value.lower():
                suspicious_found = True
                if not silent:
                    self.vm.print_output(f"[ALERT] Suspicious 'format' signature in RAM key: {key}")
                if delete:
                    self.vm.ram.memory.pop(key, None)
                    if not silent:
                        self.vm.print_output(f"[REMOVED] RAM entry {key} isolated and deleted.")
                    else:
                        self.vm.print_output(f"[AMS SILENT WARNING] Malicious code deleted from RAM.")

        for letter, disk in list(self.vm.drives.items()):
            def scan_folder(path):
                nonlocal suspicious_found

                for item in disk.list_dir(path):
                    item_path = path.rstrip("/") + "/" + item if path != "/" else "/" + item

                    if disk.is_folder(item_path):
                        scan_folder(item_path)
                        continue

                    content = disk.read_file(item_path)

                    if content != "[File not found]" and "format," in content.lower():
                        suspicious_found = True

                        if not silent:
                            self.vm.print_output(f"[ALERT] Suspicious 'format' signature found in {letter}:{item_path}")

                        if delete:
                            disk.delete_file(item_path)
                            self.vm.ram.pop(f"{letter}:{item_path}", None)

                            if not silent:
                                self.vm.print_output(f"[REMOVED] File {letter}:{item_path} securely deleted.")
                            else:
                                self.vm.print_output(f"[AMS SILENT WARNING] Malicious file {item_path} neutralized.")

            scan_folder("/")

        if not suspicious_found and not silent:
            self.vm.print_output("Scan complete. No suspicious activity found.")

        return suspicious_found


class MiniEditor:
    def __init__(self, vm):
        self.vm = vm
        self.current_drive = vm.current_drive
        self.current_file = None
        self.buffer = []
        self.clipboard = ""
        self.running = False
        self.in_prompt = None
        self.prompt_text = ""

    def open(self, filename=None):
        self.running = True
        self.current_drive = self.vm.current_drive
        self.current_file = None
        self.buffer = []
        self.clipboard = ""
        self.in_prompt = None
        self.prompt_text = ""

        if filename:
            try:
                drive, path = self.vm.resolve_path(filename)
                content = self.vm.drives[drive].read_file(path)
                if content not in ("[File not found]", "[Is a directory]"):
                    self.current_drive = drive
                    self.current_file = path
                    self.buffer = content.splitlines()
            except Exception:
                self.buffer = []

        if self.vm.output:
            self._open_gui()
        else:
            self._open_terminal()

    def _open_gui(self):
        self.vm.clear_gui()
        self.vm.output.insert("end", "══════════════════ PY-DOS Mini Editor ══════════════════\n")
        self.vm.output.insert("end", "CTRL+N: New | CTRL+O: Open | CTRL+S: Save | CTRL+C: Cut | CTRL+P: Paste | ESC: Exit\n")
        self.vm.output.insert("end", "──────────────────────────────────────────────────────────\n")

        if self.buffer:
            self.vm.output.insert("end", "\n".join(self.buffer))

        self.vm.output.focus_set()
        self.vm.output.bind("<KeyPress>", self.keypress)

    def keypress(self, event):
        if not self.running:
            return

        if self.in_prompt:
            return self._handle_prompt_keypress(event)

        if event.keysym == "Escape":
            self.close()
            return "break"

        is_ctrl = bool(event.state & 0x4)
        key = event.keysym.lower()

        if is_ctrl:
            if key == "s":
                self.save()
                return "break"
            elif key == "o":
                self.prompt_open()
                return "break"
            elif key == "n":
                self.new_file()
                return "break"
            elif key == "c":
                self.cut()
                return "break"
            elif key == "p":
                self.paste()
                return "break"

        return

    def prompt_open(self):
        self.in_prompt = "open"
        self.prompt_text = ""
        self._update_prompt_display()

    def prompt_save(self):
        self.in_prompt = "save"
        self.prompt_text = ""
        self._update_prompt_display()

    def _handle_prompt_keypress(self, event):
        if event.keysym == "Escape":
            self.in_prompt = None
            self.prompt_text = ""
            self._redraw_gui("Action cancelled.")
            return "break"

        if event.keysym == "Return":
            target = self.prompt_text.strip()
            mode = self.in_prompt
            self.in_prompt = None
            self.prompt_text = ""

            if mode == "open":
                if target:
                    self._do_open(target)
                else:
                    self._redraw_gui()
            elif mode == "save":
                if target:
                    self.current_drive, self.current_file = self.vm.resolve_path(target)
                    self.save()
                else:
                    self._redraw_gui()
            return "break"

        if event.keysym == "BackSpace":
            if len(self.prompt_text) > 0:
                self.prompt_text = self.prompt_text[:-1]
                self._update_prompt_display()
            return "break"

        if event.char and ord(event.char) >= 32:
            self.prompt_text += event.char
            self._update_prompt_display()
            return "break"

        return "break"

    def _update_prompt_display(self):
        prefix = "Open File Path: " if self.in_prompt == "open" else "Save As File Path: "
        self.vm.output.delete("end-1c linestart", "end")
        self.vm.output.insert("end", f"\n[{prefix}{self.prompt_text}_]")
        self.vm.output.see("end")

    def _do_open(self, filename):
        try:
            drive, path = self.vm.resolve_path(filename)
            content = self.vm.drives[drive].read_file(path)
            if content in ("[File not found]", "[Is a directory]"):
                self._redraw_gui(f"Error: File not found: {filename}")
                return
            self.current_drive = drive
            self.current_file = path
            self.buffer = content.splitlines()
            self._redraw_gui(f"Successfully opened: {drive}:{path}")
        except Exception as exc:
            self._redraw_gui(f"Error opening file: {exc}")

    def _redraw_gui(self, status_msg=None):
        self.vm.clear_gui()
        self.vm.output.insert("end", "══════════════════ PY-DOS Mini Editor ══════════════════\n")
        self.vm.output.insert("end", "CTRL+N: New | CTRL+O: Open | CTRL+S: Save | CTRL+C: Cut | CTRL+P: Paste | ESC: Exit\n")
        self.vm.output.insert("end", "──────────────────────────────────────────────────────────\n")
        if self.buffer:
            self.vm.output.insert("end", "\n".join(self.buffer))
        if status_msg:
            self.vm.output.insert("end", f"\n\n[{status_msg}]")
        self.vm.output.see("end")
        self.vm.output.focus_set()

    def new_file(self):
        self.current_file = None
        self.buffer = []
        self._redraw_gui("New File Created")

    def save(self):
        if not self.current_file:
            self.prompt_save()
            return

        content = self.vm.output.get("4.0", "end-1c")
        
        if "\n[Save As File Path:" in content:
            content = content.split("\n[Save As File Path:")[0]
        elif "\n\n[" in content:
            content = content.split("\n\n[")[0]

        disk = self.vm.drives.get(self.current_drive)
        if disk and disk.write_file(self.current_file, content):
            self.vm.ram.load(f"{self.current_drive}:{self.current_file}", content)
            self.buffer = content.splitlines()
            self._redraw_gui(f"File saved successfully: {self.current_drive}:{self.current_file}")
        else:
            self._redraw_gui("Error: Save operation failed!")

    def cut(self):
        try:
            if self.vm.output.tag_ranges("sel"):
                self.clipboard = self.vm.output.get("sel.first", "sel.last")
                self.vm.output.delete("sel.first", "sel.last")
            else:
                cursor = self.vm.output.index("insert")
                line_start = f"{cursor} linestart"
                line_end = f"{cursor} lineend + 1c"
                self.clipboard = self.vm.output.get(line_start, line_end)
                self.vm.output.delete(line_start, line_end)
        except tk.TclError:
            pass

    def paste(self):
        if self.clipboard:
            try:
                self.vm.output.insert("insert", self.clipboard)
            except tk.TclError:
                pass

    def close(self):
        self.running = False
        if self.vm.output:
            self.vm.output.bind("<KeyPress>", self.vm._terminal_keypress)
        self.vm.clear_gui()
        self.vm._start_terminal_input()

    def _open_terminal(self):
        print("══════════════════ PY-DOS Mini Editor ══════════════════")
        print("Commands / Shortcuts: :n (New), :o (Open), :s (Save), :c (Cut), :p (Paste), :exit / ESC")
        print("──────────────────────────────────────────────────────────")
        if self.buffer:
            for i, line in enumerate(self.buffer, 1):
                print(f"{i}: {line}")
        print("Type text lines or commands (starting with :):")

        while self.running:
            try:
                line = input().rstrip()
                if line.startswith(":") or line.upper() in ("ESC", "EXIT"):
                    cmd = line[1:].strip().lower() if line.startswith(":") else line.strip().lower()
                    if cmd in ("exit", "esc", "quit"):
                        self.running = False
                        break
                    elif cmd == "n":
                        self.current_file = None
                        self.buffer = []
                        print("New file created.")
                    elif cmd.startswith("o"):
                        parts = cmd.split(maxsplit=1)
                        target = parts[1] if len(parts) > 1 else input("Open file path: ").strip()
                        if target:
                            drive, path = self.vm.resolve_path(target)
                            content = self.vm.drives[drive].read_file(path)
                            if content in ("[File not found]", "[Is a directory]"):
                                print(f"Error: File not found: {target}")
                            else:
                                self.current_drive = drive
                                self.current_file = path
                                self.buffer = content.splitlines()
                                print(f"Successfully opened {drive}:{path}")
                    elif cmd.startswith("s"):
                        parts = cmd.split(maxsplit=1)
                        if len(parts) > 1:
                            target = parts[1]
                            self.current_drive, self.current_file = self.vm.resolve_path(target)
                        elif not self.current_file:
                            target = input("Save as file path: ").strip()
                            if target:
                                self.current_drive, self.current_file = self.vm.resolve_path(target)

                        if self.current_file:
                            content = "\n".join(self.buffer)
                            disk = self.vm.drives.get(self.current_drive)
                            if disk and disk.write_file(self.current_file, content):
                                self.vm.ram.load(f"{self.current_drive}:{self.current_file}", content)
                                print(f"File saved successfully: {self.current_drive}:{self.current_file}")
                            else:
                                print("Error: Save operation failed.")
                        else:
                            print("Error: No file specified to save.")
                    elif cmd.startswith("c"):
                        parts = cmd.split(maxsplit=1)
                        idx = int(parts[1]) - 1 if len(parts) > 1 and parts[1].isdigit() else len(self.buffer) - 1
                        if 0 <= idx < len(self.buffer):
                            self.clipboard = self.buffer.pop(idx)
                            print(f"Cut line {idx+1}: {self.clipboard}")
                        else:
                            print("Error: Invalid line index.")
                    elif cmd == "p":
                        if self.clipboard:
                            self.buffer.append(self.clipboard)
                            print(f"Pasted: {self.clipboard}")
                        else:
                            print("Error: Clipboard is empty.")
                    elif cmd == "show":
                        for i, l in enumerate(self.buffer, 1):
                            print(f"{i}: {l}")
                    else:
                        print("Unknown command. Use :n, :o, :s, :c, :p, :show, :exit")
                else:
                    self.buffer.append(line)
            except (KeyboardInterrupt, EOFError):
                break


class VirtualMachine:
    def __init__(self, vm_name):
        vm_dir = self.find_vm_dir(vm_name)
        if not vm_dir:
            raise FileNotFoundError(f"VM '{vm_name}' not found in {VMS_DIR}")

        self.vm_dir = vm_dir
        self.config_path = os.path.join(vm_dir, "config.json")
        self.config = read_json(self.config_path, {})

        if not isinstance(self.config, dict):
            raise ValueError("Invalid config.json")

        self.name = self.config.get("name", os.path.basename(vm_dir))
        self.version = str(self.config.get("version", "3.0"))
        self.disk_size_kb = int(self.config.get("disk_mb", 512)) * 1024
        self.ram_size_kb = int(self.config.get("ram_mb", 128)) * 1024

        self.system_folder = self._ensure_system_folder()
        self.config["system_folder"] = self.system_folder

        requested_disk = self.config.get("disk_filename", f"{self.name}.pydos")
        disk_path = find_case_insensitive(self.vm_dir, requested_disk)

        if disk_path is None:
            disk_path = os.path.join(self.vm_dir, f"{self.name}.pydos")
            Disk(disk_path, self.disk_size_kb).format_disk()

        self.disk_path = disk_path
        self.disk = Disk(self.disk_path, self.disk_size_kb)

        self.drives = {"C": self.disk}
        self.current_drive = "C"
        self.current_dirs = {"C": "/"}

        self.ram = RAM(self.ram_size_kb)
        self.cpu = CPU()
        self.ams = AntiMalware(self)
        self.app_depth = 0 

        self.current_dir = "/"
        self.running = True
        self.tk_running = False
        self.booted = False

        self.gui_root = None
        self.output = None
        self.input_start = None
        self._history = []
        self._history_index = None
        
        self._waiting_for_input = False
        self._gui_input_result = ""

        self._save_config()

    @staticmethod
    def find_vm_dir(vm_name):
        target = vm_name.strip().casefold()
        if not os.path.isdir(VMS_DIR):
            return None

        for entry in os.listdir(VMS_DIR):
            full = os.path.join(VMS_DIR, entry)
            if os.path.isdir(full) and entry.casefold() == target:
                return full
        return None

    def _save_config(self):
        write_json(self.config_path, self.config)

    def _ensure_system_folder(self):
        existing = self.config.get("system_folder")
        if existing and isinstance(existing, str):
            path = os.path.join(self.vm_dir, existing)
            if os.path.isdir(path):
                return existing

        while True:
            folder = random_folder_name()
            path = os.path.join(self.vm_dir, folder)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                return folder

    def sync_current_dir(self):
        self.current_dir = self.current_dirs.get(self.current_drive, "/")

    def get_prompt(self):
        self.sync_current_dir()
        if self.current_dir == "/":
            return f"{self.current_drive}:\\>"
        return f"{self.current_drive}:\\" + self.current_dir.strip("/").replace("/", "\\") + ">"

    def resolve_path(self, path):
        path = path.strip()
        if not path:
            self.sync_current_dir()
            return self.current_drive, self.current_dir

        drive = self.current_drive
        raw = path

        if len(raw) >= 2 and raw[1] == ":" and raw[0].isalpha():
            drive = raw[0].upper()
            raw = raw[2:]

            if drive not in self.drives:
                raise FileNotFoundError(f"Drive {drive}: not found.")

            if not raw:
                return drive, self.current_dirs.get(drive, "/")

            if raw.startswith("\\") or raw.startswith("/"):
                return drive, normalize_path(raw)

            return drive, normalize_path(self.current_dirs.get(drive, "/") + "/" + raw)

        if raw.startswith("\\") or raw.startswith("/"):
            return drive, normalize_path(raw)

        return drive, normalize_path(self.current_dirs.get(drive, "/") + "/" + raw)

    def set_current_dir(self, drive, path):
        if drive not in self.drives:
            return False

        self.current_dirs[drive] = normalize_path(path)
        self.current_drive = drive
        self.sync_current_dir()
        return True

    def _next_free_drive(self):
        for letter in "ABDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in self.drives:
                return letter
        return None

    def mount_pyimg(self, filename):
        host_path = os.path.abspath(filename)
        if not os.path.isfile(host_path):
            self.print_output(f"[PYIMG Error] Disk image not found: {os.path.basename(filename)}")
            return None

        if not host_path.casefold().endswith(".pyimg"):
            self.print_output("[PYIMG Error] Only .pyimg files can be mounted.")
            return None

        image_data = read_json(host_path, None)
        if not isinstance(image_data, dict):
            self.print_output("[PYIMG Error] Invalid disk image format.")
            return None

        header = image_data.get("__disk__")
        if not isinstance(header, dict) or header.get("format") != "pydos":
            self.print_output("[PYIMG Error] Not a valid PY-DOS disk image.")
            return None

        letter = self._next_free_drive()
        if letter is None:
            self.print_output("[PYIMG Error] No free drive letters available.")
            return None

        capacity = int(header.get("capacity_kb", self.disk_size_kb))
        self.drives[letter] = Disk(host_path, capacity, create=False)
        self.current_dirs[letter] = "/"

        self.print_output(f"[PYIMG] Successfully mounted {os.path.basename(host_path)} as drive {letter}:")
        return letter

    def unmount_drive(self, drive):
        drive = drive.upper()

        if drive == "C":
            self.print_output("Error: Cannot eject main system drive (C:).")
            return False

        if drive not in self.drives:
            self.print_output(f"Error: Drive {drive}: not found or not mounted.")
            return False

        del self.drives[drive]
        self.current_dirs.pop(drive, None)

        if self.current_drive == drive:
            self.current_drive = "C"
            self.sync_current_dir()

        self.print_output(f"Drive {drive}: ejected successfully.")
        return True

    def _handle_host_file_import(self, filename):
        if not filename.casefold().endswith(".pyimg"):
            self.print_output("Error: Only .pyimg disk images can be inserted.")
            return False
        return self.mount_pyimg(filename) is not None

    def tree_command(self, path, drive=None):
        drive = drive or self.current_drive
        disk = self.drives.get(drive)

        if disk is None:
            self.print_output(f"Error: Drive {drive}: not found.")
            return

        def print_tree(current_path, prefix=""):
            items = disk.list_dir(current_path)
            total = len(items)

            for i, item in enumerate(items):
                item_path = current_path.rstrip("/") + "/" + item if current_path != "/" else "/" + item
                is_dir = disk.is_folder(item_path)
                connector = "└── " if i == total - 1 else "├── "
                self.print_output(prefix + connector + item)

                if is_dir:
                    extension = " " if i == total - 1 else "│ "
                    print_tree(item_path, prefix + extension)

        self.print_output(f"{drive}:{path}")
        print_tree(path)

    def write(self, filename, content):
        drive, path = self.resolve_path(filename)
        disk = self.drives[drive]
        self.ram.load(f"{drive}:{path}", content)

        if disk.write_file(path, content):
            self.print_output("Data written successfully to disk.")
        else:
            self.print_output("Error: Write operation failed due to insufficient space or invalid path.")

    # --- NATIVE GUI TERMINAL INPUT HELPERS ---
    def terminal_gui_input(self, prompt_text):
        if not self.tk_running or not self.output:
            try:
                return input(prompt_text)
            except EOFError:
                return ""
                
        self.output.insert("end", str(prompt_text))
        self.output.see("end")
        self.input_start = self.output.index("end-1c")
        self.output.mark_set("insert", "end")
        self.output.focus_set()
        
        self._waiting_for_input = True
        self._gui_input_result = ""
        
        while self._waiting_for_input and self.tk_running:
            self.gui_root.update()
            time.sleep(0.01)
            
        return self._gui_input_result

    def terminal_gui_wait(self, prompt_text):
        if not self.tk_running or not self.output:
            input(prompt_text)
            return
            
        self.output.insert("end", str(prompt_text))
        self.output.see("end")
        self.input_start = None 
        self._waiting_for_input = True
        self._gui_input_result = ""
        
        while self._waiting_for_input and self.tk_running:
            self.gui_root.update()
            time.sleep(0.01)
    # ----------------------------------------

    def execute_app(self, filename, from_gui=False):
        if self.app_depth >= 20:
            self.print_output("\n[AMS PROTECTION] Maximum recursion depth exceeded (App Stack Limit: 20)!")
            self.print_output("Execution halted to prevent system crash.")
            return
            
        drive, path = self.resolve_path(filename)

        if not path.casefold().endswith(".app"):
            path += ".app"

        disk = self.drives.get(drive)
        if disk is None:
            self.print_output(f"Error: Drive {drive}: not found.")
            return

        content = disk.read_file(path)
        if content in ("[File not found]", "[Is a directory]"):
            self.print_output(f"Error: Application not found: {drive}:{path}")
            return

        lines = content.splitlines()
        if not lines:
            self.print_output(f"Error: Cannot run {path}, it is an empty application.")
            return
            
        self.app_depth += 1
        try:
            labels = {}
            echo_enabled = True
            env_vars = {} 
            
            import datetime
            env_vars["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
            env_vars["time"] = datetime.datetime.now().strftime("%H:%M:%S")

            for index, raw_line in enumerate(lines):
                stripped = raw_line.strip()
                if stripped.startswith(":") and not stripped.startswith("::"):
                    labels[stripped[1:].strip().lower()] = index

            index = 0
            guard = 0

            while index < len(lines):
                guard += 1
                if guard > 30000:
                    self.print_output("\n[AMS Protection] Infinite loop or excessive execution detected!")
                    self.print_output("Application process stopped to prevent system lockup.")
                    break

                raw_line = lines[index].strip()
                index += 1

                if not raw_line or raw_line.startswith(":") or raw_line.startswith("::"):
                    continue

                if raw_line.startswith("@"):
                    raw_line = raw_line[1:].lstrip()

                if not raw_line:
                    continue

                line = re.sub(r'%([^%]+)%', lambda m: env_vars.get(m.group(1).lower(), ""), raw_line)
                lowered = line.lower()

                if lowered == "echo off":
                    echo_enabled = False
                    continue
                if lowered == "echo on":
                    echo_enabled = True
                    continue
                if lowered == "echo":
                    self.print_output("")
                    continue
                if lowered.startswith("echo."):
                    self.print_output("")
                    continue
                if lowered.startswith("echo "):
                    self.print_output(line[5:])
                    continue

                if lowered == "cls" or lowered == "clear":
                    if from_gui:
                        self.clear_gui()
                    else:
                        self.print_output("\n" * 30)
                    continue

                if lowered == "pause":
                    if from_gui:
                        self.terminal_gui_wait("Press Enter to continue...")
                    else:
                        input("Press Enter to continue...")
                    continue

                if lowered.startswith("timeout"):
                    parts = lowered.split()
                    if "/t" in parts:
                        try:
                            idx = parts.index("/t")
                            sec = int(parts[idx+1])
                            if from_gui:
                                self.gui_root.update()
                            time.sleep(sec)
                        except (ValueError, IndexError):
                            pass
                    continue

                if lowered.startswith("set /p "):
                    try:
                        cmd_part = line[7:].strip()
                        var_name, prompt_text = cmd_part.split("=", 1)
                        var_name = var_name.strip().lower()
                        
                        if from_gui:
                            val = self.terminal_gui_input(prompt_text)
                            env_vars[var_name] = val if val else ""
                        else:
                            val = input(prompt_text)
                            env_vars[var_name] = val
                    except ValueError:
                        self.print_output(f"Syntax error in SET /P: {line}")
                    continue

                if lowered.startswith("menu "):
                    try:
                        # Extract arguments using regex to keep quoted strings intact
                        args = re.findall(r'"([^"]*)"', line[5:])
                        
                        if len(args) > 1:
                            menu_title = args[0]
                            menu_options = args[1:]
                            
                            # Initialize and open the Menu UI
                            mu = MenuUI(self, menu_title, menu_options)
                            choice = mu.open()
                            
                            # Export the selection to the environment variable
                            env_vars["menu_choice"] = choice
                            
                            # Clear screen for the next command if running in GUI
                            if from_gui:
                                self.clear_gui()
                        else:
                            self.print_output("Error: 'menu' command requires a title and at least one option.")
                    except Exception as e:
                        self.print_output(f"Syntax error in menu command: {e}")
                    continue
                if lowered.startswith("goto "):
                    label = line[5:].strip().lower()
                    if label in labels:
                        index = labels[label]
                    else:
                        self.print_output(f"Error: Label '{label}' not found.")
                    continue

                if lowered.startswith("if "):
                    try:
                        condition_part, rest = line[3:].split(" goto ", 1)
                        left, right = condition_part.split("==")
                        left = left.strip().strip('"')
                        right = right.strip().strip('"')
                        
                        if left == right:
                            target = rest.strip().lower()
                            if target in labels:
                                index = labels[target]
                    except ValueError:
                        self.print_output(f"Syntax error in IF command: {line}")
                    continue

                if lowered == "rem" or lowered.startswith("rem "):
                    continue

                if echo_enabled:
                    self.print_output(f"{drive}:{path}> {line}")

                for subcmd_line in line.split(";"):
                    subcmd_line = subcmd_line.strip()
                    if not subcmd_line:
                        continue

                    sub_tokens = self.cpu.execute(subcmd_line)
                    self.execute_command(sub_tokens, from_gui=from_gui, from_app=True)

                    if not self.running:
                        return
        finally:
            self.app_depth -= 1

    def execute_command(self, tokens, from_gui=False, from_app=False):
        if not tokens:
            return self.current_dir

        cmd = tokens[0].lower()

        if self.ams.enabled and not from_app:
            self.ams.scan(silent=True, delete=True)

        self.ams.record_command(cmd)

        if cmd == "exit":
            self.running = False
            self.print_output("Exiting PY-DOS...")

        elif cmd == "help":
            if len(tokens) > 1 and tokens[1].lower() in ("/all", "/a"):
                help_text = [
                    "================ PY-DOS HELP ================",
                    "DIR       : List files and directories",
                    "HELP      : Show short command list",
                    "HELP /ALL : Show all commands",
                    "TREE      : Show folder structure",
                    "TYPE      : Display file contents",
                    "WRITE     : Create or overwrite a file",
                    "DEL       : Delete a file",
                    "RENAME    : Rename a file",
                    "COPY      : Copy a file",
                    "MKDIR     : Create a folder",
                    "CD        : Change directory",
                    "C:        : Switch to C drive",
                    "A:        : Switch to A drive",
                    "RUN       : Execute a .app application",
                    "SAVE      : Save RAM contents to disk",
                    "RAMLOAD   : Load data into RAM",
                    "RAMCLEAR  : Clear RAM",
                    "RAMSHOW   : Show RAM contents",
                    "SYSINFO   : Display CPU, RAM and Disk info",
                    "REBOOT    : Save RAM and restart",
                    "FORMAT    : Format current drive",
                    "PRINT     : Print text",
                    "CLEARCPU  : Reset CPU cycles",
                    "AMS       : Run Anti-Malware Service report",
                    "AMS /SCAN : Run full AMS deep scan",
                    "AMS /DISABLE : Disable automatic AMS scanning",
                    "AMS /ENABLE  : Enable automatic AMS scanning",
                    "EDIT      : Start Mini Editor",
                    "INSERT    : Mount a .pyimg disk",
                    "EJECT     : Eject a mounted drive",
                    "CLS/CLEAR : Clear terminal screen",
                    "SHUTDOWN  : Shut down PY-DOS",
                    "EXIT      : Exit PY-DOS"
                ]

                for line in help_text:
                    self.print_output(line)
            else:
                self.print_output("=== PY-DOS HELP ===")
                self.print_output("DIR, HELP /ALL, TREE, TYPE, WRITE, DEL, RENAME, COPY, MKDIR, CD, RUN")
                self.print_output("SAVE, RAMLOAD, RAMCLEAR, RAMSHOW, SYSINFO, REBOOT, FORMAT, PRINT")
                self.print_output("CLEARCPU, AMS, AMS /SCAN, AMS /DISABLE, AMS /ENABLE, EDIT, INSERT, EJECT, CLS, SHUTDOWN, EXIT")
                self.print_output("Note: Type the name of a .app file directly to run it without 'RUN'.")

        elif len(tokens) == 1 and len(tokens[0]) == 2 and tokens[0][1] == ":" and tokens[0][0].isalpha():
            drive = tokens[0][0].upper()
            if drive in self.drives:
                self.current_drive = drive
                self.sync_current_dir()
            else:
                self.print_output(f"Error: Drive {drive}: not found.")

        elif cmd == "print":
            self.print_output(" ".join(tokens[1:]))

        elif cmd == "edit":
            filename = tokens[1] if len(tokens) > 1 else None
            MiniEditor(self).open(filename)

        elif cmd == "write":
            if len(tokens) < 3:
                self.print_output("Usage: WRITE filename content")
            else:
                self.write(tokens[1], " ".join(tokens[2:]))

        elif cmd == "type":
            if len(tokens) < 2:
                self.print_output("Usage: TYPE filename")
            else:
                drive, path = self.resolve_path(tokens[1])
                self.print_output(self.drives[drive].read_file(path))

        elif cmd == "dir":
            target = tokens[1] if len(tokens) > 1 else None
            if target:
                drive, path = self.resolve_path(target)
            else:
                drive = self.current_drive
                path = self.current_dir

            disk = self.drives.get(drive)
            if disk is None:
                self.print_output(f"Error: Drive {drive}: not found.")
                return self.current_dir

            items = disk.list_dir(path)
            if items:
                for item in items:
                    item_path = path.rstrip("/") + "/" + item if path != "/" else "/" + item
                    if disk.is_folder(item_path):
                        self.print_output(f"<DIR> {item}")
                    else:
                        self.print_output(f"      {item}")
            else:
                self.print_output("Directory is empty. No files or subdirectories found.")

        elif cmd == "tree":
            target = tokens[1] if len(tokens) > 1 else None
            if target:
                drive, path = self.resolve_path(target)
            else:
                drive = self.current_drive
                path = self.current_dir

            self.tree_command(path, drive)

        elif cmd == "mkdir":
            if len(tokens) < 2:
                self.print_output("Usage: MKDIR foldername")
            else:
                drive, path = self.resolve_path(tokens[1])
                if not self.drives[drive].mkdir(path):
                    self.print_output("Error: Unable to create directory. Path may exist or disk is full.")
                else:
                    self.print_output("Directory created successfully.")

        elif cmd == "cd":
            if len(tokens) < 2:
                self.print_output("Usage: CD foldername")
            else:
                drive, new_path = self.resolve_path(tokens[1])
                if self.drives[drive].is_folder(new_path):
                    self.set_current_dir(drive, new_path)
                else:
                    self.print_output(f"Error: Directory not found: {tokens[1]}")

        elif cmd == "copy":
            if len(tokens) < 3:
                self.print_output("Usage: COPY source_file destination_file")
            else:
                src_drive, src_path = self.resolve_path(tokens[1])
                dst_drive, dst_path = self.resolve_path(tokens[2])

                content = self.ram.get(f"{src_drive}:{src_path}")
                if content is None:
                    content = self.drives[src_drive].read_file(src_path)

                if content == "[File not found]":
                    self.print_output(f"Error: Source file '{tokens[1]}' not found.")
                elif self.drives[dst_drive].write_file(dst_path, content):
                    self.ram.load(f"{dst_drive}:{dst_path}", content)
                    self.print_output("File copied successfully.")
                else:
                    self.print_output("Error: Copy operation failed.")

        elif cmd == "rename":
            if len(tokens) < 3:
                self.print_output("Usage: RENAME old_filename new_name")
            else:
                old_drive, old_path = self.resolve_path(tokens[1])
                new_drive, new_path = self.resolve_path(tokens[2])

                if old_drive != new_drive:
                    self.print_output("Error: RENAME cannot move files between different drives.")
                else:
                    content = self.drives[old_drive].read_file(old_path)
                    if content == "[File not found]":
                        self.print_output(f"Error: File '{tokens[1]}' not found.")
                    elif self.drives[old_drive].is_folder(old_path):
                        self.print_output("Error: RENAME currently only supports files, not directories.")
                    elif (
                        self.drives[old_drive].delete_file(old_path)
                        and self.drives[new_drive].write_file(new_path, content)
                    ):
                        self.ram.pop(f"{old_drive}:{old_path}", None)
                        self.ram.load(f"{new_drive}:{new_path}", content)
                        self.print_output("File renamed successfully.")
                    else:
                        self.print_output("Error: Rename operation failed.")

        elif cmd == "del":
            if len(tokens) < 2:
                self.print_output("Usage: DEL filename")
            else:
                drive, path = self.resolve_path(tokens[1])
                self.ram.pop(f"{drive}:{path}", None)

                if self.drives[drive].delete_file(path):
                    self.print_output("File deleted successfully.")
                else:
                    self.print_output("Error: File not found.")

        elif cmd == "ramload":
            if len(tokens) < 3:
                self.print_output("Usage: RAMLOAD key value")
            else:
                drive, path = self.resolve_path(tokens[1])
                value = " ".join(tokens[2:])

                if self.ram.load(f"{drive}:{path}", value):
                    self.print_output("Data loaded into RAM successfully.")
                else:
                    self.print_output("Error: RAM is full.")

        elif cmd == "ramclear":
            self.ram.clear()
            self.print_output("RAM cleared successfully.")

        elif cmd == "ramshow":
            if self.ram.memory:
                self.print_output("RAM contents:")
                for k, v in self.ram.memory.items():
                    self.print_output(f"{k} : {v}")
            else:
                self.print_output("RAM is currently empty.")

        elif cmd == "sysinfo":
            cpu_info = self.cpu.get_info()
            ram_info = self.ram.get_info()
            disk_info = self.drives["C"].get_info()

            self.print_output("-" * 50)
            self.print_output(f"PY-DOS VERSION : {self.version}")
            self.print_output(f"VM NAME        : {self.name}")
            self.print_output(f"DRIVE          : {self.current_drive}:")
            self.print_output(f"CPU            : Total Cycles: {cpu_info['cycles']}")
            self.print_output(
                f"RAM            : {ram_info['total_kb']} KB | "
                f"Used: {ram_info['used_kb']} KB | "
                f"Free: {ram_info['free_kb']} KB"
            )
            self.print_output(
                f"DISK           : {disk_info['max_kb']} KB | "
                f"Used: {disk_info['used_kb']} KB | "
                f"Free: {disk_info['free_kb']} KB | "
                f"Files: {disk_info['file_count']}"
            )
            self.print_output("DRIVES         : " + ", ".join(f"{letter}:" for letter in self.drives))
            self.print_output("-" * 50)

        elif cmd == "save":
            self.drives["C"].write_bulk(self.ram.memory)
            self.print_output("RAM contents saved to disk successfully.")

        elif cmd == "reboot":
            self.drives["C"].write_bulk(self.ram.memory)
            self.ram.clear()
            self.cpu = CPU()
            self.current_drive = "C"
            self.current_dirs = {letter: path for letter, path in self.current_dirs.items() if letter in self.drives}
            self.current_dirs.setdefault("C", "/")
            self.sync_current_dir()
            self.running = True
            self.print_output("System reboot completed successfully.")

        elif cmd == "shutdown":
            self.running = False
            self.print_output("Shutting down PY-DOS...")

        elif cmd == "format":
            confirm = None
            if from_gui:
                ans = self.terminal_gui_input(f"WARNING: All data on {self.current_drive}: will be lost. Format? (y/n): ")
                confirm = (ans.strip().lower() == "y")
            else:
                try:
                    confirm = input(f"WARNING: All data on {self.current_drive}: will be lost. Format? (y/n): ").strip().lower() == "y"
                except EOFError:
                    confirm = False

            if confirm:
                self.drives[self.current_drive].format_disk()
                self.current_dirs[self.current_drive] = "/"
                self.sync_current_dir()
                self.print_output(f"Drive {self.current_drive}: formatted successfully. All data wiped.")
            else:
                self.print_output("Format operation cancelled.")

        elif cmd == "clearcpu":
            self.cpu.clearcpu()
            self.print_output("CPU cycles reset to 0.")

        elif cmd == "ams":
            if len(tokens) == 1:
                self.print_output("=== Anti-Malware Service Deluxe Report ===")
                self.print_output(f"Status           : {'Active & Running' if self.ams.enabled else 'Disabled'}")
                self.print_output(f"Tracked Commands : {len(self.ams.command_history)}")
                self.print_output("Use 'AMS /SCAN' to perform a deep system scan.")
            else:
                subcommand = tokens[1].lower()
                if subcommand == "/scan":
                    found = self.ams.scan(silent=False, delete=True)
                    if not found:
                        self.print_output("Scan complete. System is clean.")
                elif subcommand == "/disable":
                    self.ams.enabled = False
                    self.print_output("Warning: AMS automatic scanning disabled.")
                elif subcommand == "/enable":
                    self.ams.enabled = True
                    self.print_output("AMS automatic scanning enabled.")
                else:
                    self.print_output("Usage: AMS /SCAN, AMS /ENABLE, or AMS /DISABLE")

        elif cmd == "run":
            if len(tokens) < 2:
                self.print_output("Usage: RUN filename.app")
            else:
                self.execute_app(tokens[1], from_gui=from_gui)

        elif cmd == "insert":
            if len(tokens) < 2:
                self.print_output("Usage: INSERT filename.pyimg")
            else:
                self._handle_host_file_import(tokens[1])

        elif cmd == "eject":
            if len(tokens) < 2:
                self.print_output("Usage: EJECT drive")
            else:
                self.unmount_drive(tokens[1].replace(":", ""))

        elif cmd in ("clear", "cls"):
            if from_gui:
                self.clear_gui()
            else:
                self.print_output("\n" * 30)

        else:
            drive, path = self.resolve_path(tokens[0])
            test_path = path if path.casefold().endswith(".app") else path + ".app"
            if self.drives[drive].read_file(test_path) not in ("[File not found]", "[Is a directory]"):
                self.execute_app(test_path, from_gui=from_gui)
            else:
                self.print_output(f"Bad command or file name: '{tokens[0]}'.")

        self.sync_current_dir()
        return self.current_dir

    def terminal(self):
        self.boot()
        print(f"PY-DOS v{self.version} - Booting...")
        print("Initializing CPU...")
        print("Initializing RAM...")
        print("Checking DISK...")
        print("System Boot Successful.\n")

        while self.running:
            try:
                command = input(self.get_prompt()).strip()
                if not command:
                    continue

                tokens = self.cpu.execute(command)
                self.current_dir = self.execute_command(tokens, from_gui=False)
            except KeyboardInterrupt:
                print("\nUse EXIT to quit.")
            except EOFError:
                break
            except Exception as exc:
                print(f"[SYSTEM ERROR] {exc}")

    def gui(self):
        self.gui_root = tk.Tk()
        self.gui_root.title(f"PY-DOS v{self.version} - {self.name}")
        self.gui_root.geometry("1100x700")
        self.gui_root.minsize(900, 600)
        self.gui_root.configure(bg="#080808")

        self._configure_ttk_style()
        self._build_menus()
        self._build_terminal()

        self.tk_running = True
        self.gui_root.protocol("WM_DELETE_WINDOW", self.gui_exit)
        self.gui_root.after(0, self.boot_sequence_gui)
        self.gui_root.mainloop()

    def _configure_ttk_style(self):
        style = ttk.Style(self.gui_root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Boot.TLabel", background="#080808", foreground="#e8e8e8")

    def _build_menus(self):
        bar = tk.Frame(self.gui_root, bg="#d7d7d7", bd=1, relief="raised", highlightthickness=0)
        bar.pack(side="top", fill="x")

        file_btn = tk.Menubutton(
            bar,
            text="File",
            bg="#d7d7d7",
            activebackground="#c5c5c5",
            padx=10,
            pady=4,
            bd=1,
            relief="raised",
            highlightthickness=1,
            highlightbackground="#8c8c8c"
        )

        file_menu = tk.Menu(file_btn, tearoff=False, bd=1)
        file_menu.add_command(label="Help", command=self.show_help)
        file_menu.add_command(label="About", command=self.show_about)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.gui_exit)

        file_btn.configure(menu=file_menu)
        file_btn.pack(side="left", padx=(4, 2), pady=3)

        machine_btn = tk.Menubutton(
            bar,
            text="Virtual Machine",
            bg="#d7d7d7",
            activebackground="#c5c5c5",
            padx=10,
            pady=4,
            bd=1,
            relief="raised",
            highlightthickness=1,
            highlightbackground="#8c8c8c"
        )

        machine_menu = tk.Menu(machine_btn, tearoff=False, bd=1)
        machine_menu.add_command(label="Shutdown", command=self.shutdown_gui)
        machine_menu.add_command(label="Restart", command=self.restart_gui)

        machine_btn.configure(menu=machine_menu)
        machine_btn.pack(side="left", padx=2, pady=3)

        disk_btn = tk.Button(
            bar,
            text="Insert Disk",
            bg="#d7d7d7",
            activebackground="#c5c5c5",
            padx=10,
            pady=4,
            bd=1,
            relief="raised",
            highlightthickness=1,
            highlightbackground="#8c8c8c",
            command=self.insert_disk
        )
        disk_btn.pack(side="left", padx=(2, 4), pady=3)

    def _build_terminal(self):
        terminal_frame = tk.Frame(self.gui_root, bg="#080808", bd=1, relief="sunken", highlightthickness=0)
        terminal_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.output = tk.Text(
            terminal_frame,
            bg="#080808",
            fg="#f0f0f0",
            insertbackground="#ffffff",
            selectbackground="#404040",
            selectforeground="#ffffff",
            wrap="char",
            font=("Consolas", 11),
            bd=0,
            relief="flat",
            padx=10,
            pady=8,
            undo=False,
            highlightthickness=0
        )
        self.output.pack(fill="both", expand=True)

        self.output.bind("<KeyPress>", self._terminal_keypress)
        self.output.bind("<Button-1>", self._terminal_click)
        self.output.bind("<MouseWheel>", self._terminal_mousewheel)
        self.output.focus_set()

    def boot_sequence_gui(self):
        if not self.running:
            return

        self.boot(reset_runtime=True)
        self.clear_gui()

        lines = [
            f"PY-DOS v{self.version} - Booting...",
            "Initializing CPU...",
            "Initializing RAM...",
            "Checking DISK...",
            "System Boot Successful."
        ]

        for line in lines:
            self.print_output(line)

        self._start_terminal_input()

    def boot(self, reset_runtime=True):
        if reset_runtime or not self.booted:
            self.cpu = CPU()
            self.ram = RAM(self.ram_size_kb)
            self.disk = Disk(self.disk_path, self.disk_size_kb)
            self.drives = {"C": self.disk}
            self.current_drive = "C"
            self.current_dirs = {"C": "/"}

        self.running = True
        self.booted = True
        self.sync_current_dir()

    def _start_terminal_input(self):
        if not self.output:
            return

        self.output.insert("end", self.get_prompt())
        self.input_start = self.output.index("end-1c")
        self.output.mark_set("insert", "end")
        self.output.focus_set()

    def _terminal_click(self, _event=None):
        if self.output:
            self.output.mark_set("insert", "end")
            self.output.focus_set()
        return "break"

    def _terminal_mousewheel(self, event):
        self.output.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _terminal_keypress(self, event):
        if not self.running:
            return "break"

        key = event.keysym

        # --- YENİ GUI İÇİ TERMİNAL GİRDİ YÖNETİMİ ---
        if getattr(self, "_waiting_for_input", False):
            if key == "Return":
                if getattr(self, "input_start", None):
                    self._gui_input_result = self.output.get(self.input_start, "end-1c").strip()
                else:
                    self._gui_input_result = ""
                self.output.insert("end", "\n")
                self.output.see("end")
                self._waiting_for_input = False
                return "break"
            
            if key == "BackSpace":
                if getattr(self, "input_start", None) and self.output.compare("insert", ">", self.input_start):
                    self.output.delete("insert-1c", "insert")
                return "break"
            
            if getattr(self, "input_start", None) is None:
                return "break" 
                
            if event.char and ord(event.char) >= 32:
                self.output.insert("end", event.char)
                self.output.see("end")
            return "break"
        # -------------------------------------------

        if self.input_start is None:
            return "break"

        self.output.mark_set("insert", "end")

        if key == "Return":
            self._submit_gui_command()
            return "break"

        if key == "BackSpace":
            if self.output.compare("insert", ">", self.input_start):
                self.output.delete("insert-1c", "insert")
            return "break"

        if key == "Left":
            if self.output.compare("insert", ">", self.input_start):
                self.output.mark_set("insert", "insert-1c")
            return "break"

        if key == "Home":
            self.output.mark_set("insert", self.input_start)
            return "break"

        if key in ("Up", "Down"):
            self._history_navigate(key)
            return "break"

        if key in ("Right", "End", "Delete", "Insert", "Prior", "Next"):
            return "break"

        if event.state & 0x4 and key.lower() in ("c", "v", "x", "a"):
            return self._handle_shortcut(key)

        if event.char and ord(event.char) >= 32:
            self.output.insert("end", event.char)
            self.output.see("end")
            return "break"

        return "break"

    def _handle_shortcut(self, key):
        if key.lower() == "c":
            try:
                self.output.event_generate("<<Copy>>")
            except tk.TclError:
                pass
            return "break"

        if key.lower() == "v":
            try:
                value = self.gui_root.clipboard_get()
            except tk.TclError:
                value = ""

            if value:
                for char in value.replace("\r", ""):
                    if char == "\n":
                        continue
                    self.output.insert("end", char)
                self.output.see("end")

            return "break"

        if key.lower() == "x":
            return "break"

        if key.lower() == "a":
            self.output.tag_remove("sel", "1.0", "end")
            return "break"

        return "break"

    def _history_navigate(self, key):
        if not self._history:
            return

        if self._history_index is None:
            self._history_index = len(self._history)

        if key == "Up":
            self._history_index = max(0, self._history_index - 1)
        else:
            self._history_index = min(len(self._history), self._history_index + 1)

        value = "" if self._history_index >= len(self._history) else self._history[self._history_index]

        self.output.delete(self.input_start, "end")
        self.output.insert("end", value)
        self.output.see("end")

    def _submit_gui_command(self):
        self.output.mark_set("insert", "end")
        command = self.output.get(self.input_start, "end").strip()

        self.output.insert("end", "\n")
        self.input_start = None
        self._history_index = None

        if not command:
            if self.running:
                self._start_terminal_input()
            return

        self._history.append(command)

        try:
            tokens = self.cpu.execute(command)
            self.current_dir = self.execute_command(tokens, from_gui=True)

            if self.running:
                self._start_terminal_input()
            else:
                self.gui_root.after(0, self.gui_exit)

        except Exception as exc:
            self.print_output(f"[SYSTEM ERROR] {exc}")
            if self.running:
                self._start_terminal_input()

    def print_output(self, text):
        text = str(text)

        if self.output is None:
            print(text)
            return

        if not self.tk_running:
            return

        if not text.endswith("\n"):
            text += "\n"

        self.output.insert("end", text)
        self.output.see("end")

    def clear_gui(self):
        if not self.output:
            return

        self.output.delete("1.0", "end")
        self.input_start = None

    def show_help(self):
        text = (
            "FILE\n"
            "  Help       : Show this window.\n"
            "  About      : Show PY-DOS information.\n"
            "  Exit       : Exit the VM.\n\n"
            "VIRTUAL MACHINE\n"
            "  Shutdown   : Shut down the VM.\n"
            "  Restart    : Save RAM and restart.\n\n"
            "INSERT DISK\n"
            "  Select a .pyimg image and mount it.\n\n"
            "DRIVES\n"
            "  C:\\         : Main PY-DOS disk\n"
            "  A:\\ / B:\\   : Mounted PYIMG disks\n\n"
            "COMMANDS\n"
            "  HELP, HELP /ALL, DIR, TREE, TYPE, WRITE,\n"
            "  DEL, RENAME, COPY, MKDIR, CD, RUN,\n"
            "  SAVE, RAMLOAD, RAMCLEAR, RAMSHOW,\n"
            "  SYSINFO, REBOOT, FORMAT, PRINT,\n"
            "  CLEARCPU, AMS, AMS /SCAN,\n"
            "  AMS /DISABLE, AMS /ENABLE, EDIT, INSERT, EJECT,\n"
            "  CLS, SHUTDOWN, EXIT\n"
            "  Note: You can run apps directly by their name."
        )

        messagebox.showinfo("PY-DOS Help", text, parent=self.gui_root)
        self.output.focus_set()

    def show_about(self):
        messagebox.showinfo("About PY-DOS", f"PY-DOS v{self.version}\nCustom Build Engine", parent=self.gui_root)
        self.output.focus_set()

    def gui_exit(self):
        self.running = False
        self.tk_running = False

        if self.gui_root is not None:
            try:
                self.gui_root.destroy()
            except tk.TclError:
                pass

    def shutdown_gui(self):
        self.print_output("Machine shutdown requested.")
        self.running = False

        if self.gui_root:
            self.gui_root.after(0, self.gui_exit)

    def restart_gui(self):
        self.drives["C"].write_bulk(self.ram.memory)
        self.ram.clear()

        env = os.environ.copy()
        env["PYDOS_RESTART"] = "1"

        try:
            subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), self.name, "--gui"],
                cwd=BASE_DIR,
                env=env
            )
        finally:
            self.running = False
            if self.gui_root:
                self.gui_root.after(0, self.gui_exit)

    def insert_disk(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Insert PYIMG Disk",
            filetypes=[("PYIMG disk image", "*.pyimg"), ("All files", "*.*")],
            parent=self.gui_root
        )

        if not path:
            self.output.focus_set()
            return

        self._handle_host_file_import(path)
        self.output.focus_set()
        self._start_terminal_input()


def main():
    if len(sys.argv) < 2:
        print("Usage: python vm.py <VM_NAME> [--gui] [--terminal]")
        return

    vm_name = sys.argv[1]
    force_terminal = "--terminal" in sys.argv[2:]

    try:
        vm = VirtualMachine(vm_name)
        if force_terminal:
            vm.terminal()
        else:
            vm.gui()
    except Exception as exc:
        print(f"[SYSTEM ERROR] {exc}")
        raise


if __name__ == "__main__":
    main()
