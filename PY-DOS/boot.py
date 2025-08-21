import time, sys, ram, disk, cpu
from cpu import CPU
from ram import RAM
from disk import Disk

# --- Global Command History ---
command_history = {}
global disk_obj
disk_obj = Disk()
def record_command(cmd, ram):
    cmd_lower = cmd.lower()
    if cmd_lower not in command_history:
        command_history[cmd_lower] = 0
    command_history[cmd_lower] += 1
    if command_history[cmd_lower] > 300:
        print(f"[AMS ALERT] Command '{cmd_lower}' executed {command_history[cmd_lower]} times!")
        while True:
            choice = input("Do you want to clear the ram or reboot the system? (To exit type 'e') (c/r/e): ").strip().lower()
            if choice == "c":
                print("[AMS] Clearing ram...")
                if not disk_obj.is_folder("/ams"):
                    disk_obj.mkdir("/ams")
                disk_obj.write_file("/ams/amslog", "command_history[cmd_lower] > 300:!!!userinput:t;out:break,ramclear!")
                ram.clear()
                break
            elif choice == "r":
                print("[AMS] Rebooting the system...")
                if not disk_obj.is_folder("/ams"):
                    disk_obj.mkdir("/ams")
                disk_obj.write_file("/ams/amslog", "command_history[cmd_lower] > 300:!!!userinput:r;out:break,boot,ramclear!")
                ram.clear()
                boot()
                break
            elif choice == "e":
                print("[AMS] Exiting...")
                if not disk_obj.is_folder("/ams"):
                    disk_obj.mkdir("/ams")
                disk_obj.write_file("/ams/amslog", "command_history[cmd_lower] > 300:!!!userinput:e;out:break!")
                break
            else:
                print("Please type c/r/e ")

# --- Anti-Malware Service Deluxe ---
def ams_scan(ram, disk=None, silent=False, delete=False):
    if not silent:
        print("=== Anti-Malware Service Deluxe ===")
    suspicious_found = False

    # RAM taraması
    for key in list(ram.memory.keys()):
        if "format" in ram.memory[key].lower():
            suspicious_found = True
            if not silent:
                print(f"[ALERT] Suspicious 'format' command in RAM key: {key}")
            if delete:
                ram.memory.pop(key)
                if not silent:
                    print(f"[REMOVED] RAM entry {key} deleted")
                if silent:
                    print(f"[REMOVED] RAM entry {key} deleted")

    # Disk taraması
    if disk is not None:
        def scan_folder(path):
            nonlocal suspicious_found
            items = disk.list_dir(path)
            for item in items:
                item_path = path.rstrip("/") + "/" + item if path != "/" else "/" + item
                if disk.is_folder(item_path):
                    scan_folder(item_path)
                else:
                    content = disk.read_file(item_path)
                    if content != "[File not found]" and "format," in content.lower():
                        suspicious_found = True
                        if not silent:
                            print(f"[ALERT] Suspicious 'format' command found in {item_path}")
                        if silent:
                            print(f"[ALERT] Suspicious 'format' command found in {item_path}")
                        if delete:
                            disk.delete_file(item_path)
                            ram.memory.pop(item_path, None)
                            if not silent:
                                print(f"[REMOVED] {item_path} deleted")
                            if silent:
                                print(f"[REMOVED] {item_path} deleted")
        scan_folder("/")
    if not suspicious_found and not silent:
        print("No suspicious activity found.")
# --- Mini Editor ---
def start_editor(disk, ram, current_dir="/"):
    current_file = None
    buffer = []
    print("══════════════════ Mini Editor ═════════════════════")
    print("Type text or commands starting with ':'")
    print("Commands: :open, :new, :del, :show, :save, :exit")
    print("────────────────────────────────────────────────────")
    while True:
        line = input().rstrip()
        if line.startswith(":"):
            cmd = line[1:].strip()
            if cmd.startswith("open "):
                filename = cmd[5:].strip()
                abs_path = filename if filename.startswith("/") else f"{current_dir}/{filename}"
                content = disk.read_file(abs_path)
                if content in ("[File not found]", "[Is a directory]"):
                    print(f"File not found: {filename}")
                    buffer = []
                    current_file = None
                else:
                    buffer = content.splitlines()
                    current_file = abs_path
                    print(f"Opened {filename}")
            elif cmd.startswith("new "):
                filename = cmd[4:].strip()
                current_file = filename if filename.startswith("/") else f"{current_dir}/{filename}"
                buffer = []
                print(f"New file created: {current_file}")
            elif cmd.startswith("del "):
                try:
                    index = int(cmd[4:]) - 1
                    removed = buffer.pop(index)
                    print(f"Deleted line {index+1}: {removed}")
                except:
                    print("Invalid line number.")
            elif cmd == "show":
                for i, l in enumerate(buffer):
                    print(f"{i+1}: {l}")
            elif cmd == "save":
                if current_file:
                    content = "\n".join(buffer)
                    ram.load(current_file, content)
                    disk.write_file(current_file, content)
                    print(f"Saved: {current_file}")
                else:
                    print("No file to save.")
            elif cmd in ("exit", "quit"):
                break
            else:
                print("Unknown command.")
        else:
            buffer.append(line)

# --- Helper Functions ---
def get_abs_path(path, current_dir):
    if path.startswith("/"):
        return path
    if current_dir == "/":
        return "/" + path
    return current_dir.rstrip("/") + "/" + path

def tree_command(path, disk):
    def print_tree(current_path, prefix=""):
        items = disk.list_dir(current_path)
        total = len(items)
        for i, item in enumerate(items):
            item_path = current_path.rstrip("/") + "/" + item if current_path != "/" else "/" + item
            is_dir = disk.is_folder(item_path)
            connector = "└── " if i == total - 1 else "├── "
            print(prefix + connector + item)
            if is_dir:
                extension = " " if i == total - 1 else "│ "
                print_tree(item_path, prefix + extension)
    print(path)
    print_tree(path)

# --- Execute Commands ---
def execute_command(tokens, cpu, ram, disk, current_dir):
    if not tokens:
        return current_dir
    cmd = tokens[0].lower()
    ams_scan(ram, disk=disk, silent=True, delete=True)
    record_command(cmd, ram)

    if cmd == "exit":
        print("Exiting PY-DOS...")
        sys.exit()
    elif cmd == "help":
        print("=== PY-DOS HELP ===")
        print("DIR, HELPALL, TREE, TYPE, WRITE, DEL, RENAME, COPY, MKDIR, CD, RUN, SAVE, RAMLOAD, RAMCLEAR, RAMSHOW, SYSINFO, REBOOT, FORMAT, PRINT, CLEARCPU, AMS, EXIT")
    elif cmd == "helpall":
        print("======================= PY-DOS HELP ===========================")
        print("DIR       : List files and directories in the current folder")
        print("TREE      : Show folder structure recursively")
        print("TYPE      : Display content of a file (TYPE filename)")
        print("WRITE     : Create or overwrite a file (WRITE filename content)")
        print("DEL       : Delete a file (DEL filename)")
        print("RENAME    : Rename a file (RENAME old_name new_name)")
        print("COPY      : Copy a file (COPY source_file dest_file)")
        print("MKDIR     : Create a new folder (MKDIR foldername)")
        print("CD        : Change directory (CD foldername, CD ..)")
        print("RUN       : Execute a file (RUN filename)")
        print("SAVE      : Save RAM contents to disk")
        print("RAMLOAD   : Load key-value into RAM (RAMLOAD key value)")
        print("RAMCLEAR  : Clear all RAM contents")
        print("RAMSHOW   : Show current RAM contents")
        print("SYSINFO   : Display CPU, RAM, and Disk info")
        print("REBOOT    : Save RAM and restart PY-DOS")
        print("FORMAT    : Format the disk")
        print("PRINT     : Print text to screen (PRINT text)")
        print("CLEARCPU  : Reset CPU cycles to 0")
        print("AMS       : Run Anti-Malware Service scan")
        print("EXIT      : Exit PY-DOS")
    elif cmd == "print":
        print(" ".join(tokens[1:]))
    elif cmd == "edit":
        start_editor(disk, ram, current_dir)
    elif cmd == "write":
        if len(tokens) < 3:
            print("Usage: WRITE filename content")
        else:
            filename = get_abs_path(tokens[1], current_dir)
            content = " ".join(tokens[2:])
            ram.load(filename, content)
            disk.write_file(filename, content)
            disk.write_bulk(ram.memory)
            print(f"Written to RAM and Disk: {filename}")
    elif cmd == "type":
        if len(tokens) < 2:
            print("Usage: TYPE filename")
        else:
            filename = get_abs_path(tokens[1], current_dir)
            print(disk.read_file(filename))
    elif cmd == "dir":
        disk.write_bulk(ram.memory)
        items = disk.list_dir(current_dir)
        if items:
            for item in items:
                item_path = current_dir.rstrip("/") + "/" + item if current_dir != "/" else "/" + item
                print(f"<DIR> {item}" if disk.is_folder(item_path) else f" {item}")
        else:
            print("No files or directories.")
    elif cmd == "tree":
        tree_command(current_dir, disk)
    elif cmd == "mkdir":
        if len(tokens) < 2:
            print("Usage: MKDIR foldername")
        else:
            folder_path = get_abs_path(tokens[1], current_dir)
            disk.mkdir(folder_path)
            disk.write_bulk(ram.memory)
    elif cmd == "cd":
        if len(tokens) < 2:
            print("Usage: CD foldername")
        else:
            target = tokens[1]
            if target == "..":
                if current_dir != "/":
                    current_dir = "/".join(current_dir.rstrip("/").split("/")[:-1])
                if current_dir == "":
                    current_dir = "/"
            else:
                new_path = get_abs_path(target, current_dir)
                if disk.is_folder(new_path):
                    current_dir = new_path
                else:
                    print(f"Directory not found: {target}")
    elif cmd == "copy":
        if len(tokens) < 3:
            print("Usage: COPY source_file destination_file")
        else:
            src = get_abs_path(tokens[1], current_dir)
            dst = get_abs_path(tokens[2], current_dir)
            content = ram.get(src)
            if content is None:
                content = disk.read_file(src)
                if content == "[File not found]":
                    print(f"Source file '{src}' not found.")
                    return current_dir
            ram.load(dst, content)
            disk.write_file(dst, content)
            print(f"Copied '{src}' to '{dst}'")
    elif cmd == "rename":
        if len(tokens) < 3:
            print("Usage: RENAME old_filename new_filename")
        else:
            old_name = get_abs_path(tokens[1], current_dir)
            new_name = get_abs_path(tokens[2], current_dir)
            content = ram.get(old_name)
            if content is None:
                content = disk.read_file(old_name)
            ram.memory.pop(old_name, None)
            ram.load(new_name, content)
            disk.delete_file(old_name)
            disk.write_file(new_name, content)
            print(f"Renamed '{old_name}' to '{new_name}'")
    elif cmd == "del":
        if len(tokens) < 2:
            print("Usage: DEL filename")
        else:
            filename = get_abs_path(tokens[1], current_dir)
            ram.memory.pop(filename, None)
            disk.delete_file(filename)
            print(f"Deleted '{filename}'")
    elif cmd == "ramload":
        if len(tokens) < 3:
            print("Usage: RAMLOAD key value")
        else:
            key = get_abs_path(tokens[1], current_dir)
            value = " ".join(tokens[2:])
            ram.load(key, value)
            print(f"Loaded into RAM: {key}")
    elif cmd == "ramclear":
        ram.clear()
        print("RAM cleared.")
    elif cmd == "ramshow":
        if ram.memory:
            print("RAM contents:")
            for k, v in ram.memory.items():
                print(f"{k} : {v}")
        else:
            print("RAM is empty.")
    elif cmd == "sysinfo":
        cpu_info = cpu.get_info()
        ram_info = ram.get_info()
        disk_info = disk.get_info()
        print("-"*40)
        print(f"CPU : Cycles: {cpu_info['cycles']}")
        print(f"RAM : {ram_info['total_kb']} KB | Used: {ram_info['used_kb']} KB | Free: {ram_info['free_kb']} KB")
        print(f"DISK : {disk_info['max_kb']} KB | Used: {disk_info['used_kb']} KB | Free: {disk_info['free_kb']} KB | Files: {disk_info['file_count']}")
        print("-"*40)
    elif cmd == "reboot":
        print("Saving RAM contents to Disk and rebooting...")
        disk.write_bulk(ram.memory)
        ram.clear()
        boot()
        return current_dir
    elif cmd == "format":
        confirm = input("Are you sure you want to format the disk? (y/n): ").strip().lower()
        if confirm == "y":
            disk.format_disk()
            print("Disk formatted successfully. Rebooting...")
            ram.clear()
            boot()
        else:
            print("Format cancelled.")
    elif cmd == "clearcpu":
        cpu.clearcpu()
        print("CPU cycles cleared to 0.")
    elif cmd == "ams":
        ams_scan(ram, disk=disk, silent=False, delete=True)
    elif cmd == "run":
        if len(tokens) < 2:
            print("Usage: RUN filename")
        else:
            filename = get_abs_path(tokens[1], current_dir)
            content = disk.read_file(filename)
            if content in ("[File not found]", "[Is a directory]"):
                print(f"Application not found: {tokens[1]}")
                return current_dir
            lines = content.splitlines()
            if not lines:
                print(f"Cannot run {tokens[1]}: Empty file!")
                return current_dir
            first_line = lines[0].strip()
            if "utf8" not in first_line.lower():
                print(f"Cannot run {tokens[1]}: Access denied.")
                return current_dir
            lines_to_run = [first_line.replace("utf8","",1).strip()] if len(lines)==1 else lines[1:]
            for line in lines_to_run:
                line = line.strip()
                if not line:
                    continue
                subcommands = line.split(";")
                for subcmd_line in subcommands:
                    sub_tokens = cpu.execute(subcmd_line.strip())
                    execute_command(sub_tokens, cpu, ram, disk, current_dir)
    else:
        print(f"Bad command or file name: {cmd}")

    return current_dir

# --- Terminal ---
def start_terminal(cpu, ram, disk):
    print("\nPY-DOS v1.0\nType HELP for commands.\n")
    current_dir = "/"
    while True:
        try:
            command = input(f"C:{current_dir}> ").strip()
            tokens = cpu.execute(command)
            current_dir = execute_command(tokens, cpu, ram, disk, current_dir)
        except KeyboardInterrupt:
            print("\nUse EXIT to quit.")
        except Exception as e:
            print(f"[ERROR] {e}")

# --- Boot ---
def boot():
    print("PY-DOS v1.0 - Booting...")
    time.sleep(0.1)
    print("Initializing CPU...")
    cpu_obj = CPU()
    print("Initializing RAM...")
    ram_obj = RAM()
    time.sleep(0.05)
    print("Checking DISK...")
    disk_obj = Disk()
    time.sleep(0.05)
    print("Boot successful.")
    start_terminal(cpu_obj, ram_obj, disk_obj)

if __name__ == "__main__":
    boot()
