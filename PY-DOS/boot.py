import time, sys, json, os, ram, disk, cpu
from cpu import CPU
from ram import RAM
from disk import Disk
### --- Anti-Malware Service Deluxe --- ###
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

    # Disk taraması (sadece varsa ve delete=True ise)
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
                    if content != "[File not found]" and "format" in content.lower():
                        suspicious_found = True
                        if not silent:
                            print(f"[ALERT] Suspicious 'format' command found in {item_path}")
                        if delete:
                            disk.delete_file(item_path)
                            ram.memory.pop(item_path, None)
                            if not silent:
                                print(f"[REMOVED] {item_path} deleted")

        scan_folder("/")  

    if not suspicious_found and not silent:
        print("No suspicious content found.")

### --- Terminal --- ###
def start_terminal(cpu, ram, disk):
    print("\nPY-DOS v1.0\nType HELP for commands.\n")

    current_dir = "/"

    def get_abs_path(path):
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
                    extension = "    " if i == total - 1 else "│   "
                    print_tree(item_path, prefix + extension)

        print(path)
        print_tree(path)
    

    while True:
        try:
            command = input(f"C:{current_dir}> ").strip()
            tokens = cpu.execute(command)
            ams_scan(ram, silent=True, delete=True)

            if not tokens:
                continue

            cmd = tokens[0].lower()

            if cmd == "exit":
                print("Exiting PY-DOS...")
                break
            elif cmd == "ams":
                ams_scan(ram, disk=disk, silent=False, delete=True)
            elif cmd == "mkdir":
                if len(tokens) < 2:
                    print("Usage: MKDIR foldername")
                else:
                    folder_path = get_abs_path(tokens[1])
                    disk.mkdir(folder_path)
            elif cmd == "save":
                disk.write_bulk(ram.memory)
                print("RAM contents saved to disk.")
            elif cmd == "cd" or cmd == "ccd":
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
                        new_path = get_abs_path(target)
                        if disk.is_folder(new_path):
                            current_dir = new_path
                        else:
                            print(f"Directory not found: {target}")

############################################run app not cmd ############################################
            elif cmd == "run":
                if len(tokens) < 2:
                    print("Usage: RUN filename")
                else:
                    filename = get_abs_path(tokens[1])
                    content = disk.read_file(filename)
                    if content in ("[File not found]", "[Is a directory]"):
                        print(f"Application not found: {tokens[1]}")
                        continue

                    lines = content.splitlines()
                    if not lines:
                        print(f"Cannot run {tokens[1]}: Empty file!")
                        continue

                    first_line = lines[0].strip()
                    if "utf8" not in first_line.lower():
                        print(f"Cannot run {tokens[1]}: Access denied.")
                        continue

                    # Tek satır mı, yoksa çok satır mı
                    if len(lines) == 1:
                        # Başındaki utf8'i çıkar ve kalanını çalıştır
                        lines_to_run = [first_line.replace("utf8","",1).strip()]
                        ams_scan(ram, disk=disk, silent=True, delete=True)
                    else:
                        lines_to_run = lines[1:]

                    for line in lines_to_run:
                        line = line.strip()
                        if not line:
                            continue
                        subcommands = line.split(";")
                        for subcmd_line in subcommands:
                            parts = cpu.execute(subcmd_line.strip())
                            if not parts:
                                continue
                            subcmd = parts[0].lower()

                            # Buradan itibaren tüm alt komutlar bu girintide olmalı
                            if subcmd == "print":
                                print(" ".join(parts[1:]))

                            elif subcmd == "write":
                                fname = get_abs_path(parts[1])
                                txt = " ".join(parts[2:])
                                ram.load(fname, txt)
                                disk.write_file(fname, txt)
                                print(f"Written to RAM and Disk: {fname}")

                            elif subcmd == "type":
                                fname = get_abs_path(parts[1])
                                print(disk.read_file(fname))

                            elif subcmd == "dir":
                                items = disk.list_dir("/")
                                for item in items:
                                    print(item)

                            elif subcmd == "del":
                                fname = get_abs_path(parts[1])
                                ram.memory.pop(fname, None)
                                disk.delete_file(fname)
                                print(f"Deleted {fname}")

                            elif subcmd == "rename":
                                old_name = get_abs_path(parts[1])
                                new_name = get_abs_path(parts[2])
                                content = ram.get(old_name)
                                if content is None:
                                    content = disk.read_file(old_name)
                                ram.memory.pop(old_name, None)
                                ram.load(new_name, content)
                                disk.delete_file(old_name)
                                disk.write_file(new_name, content)
                                print(f"Renamed {old_name} to {new_name}")

                            elif subcmd == "copy":
                                src = get_abs_path(parts[1])
                                dst = get_abs_path(parts[2])
                                content = ram.get(src)
                                if content is None:
                                    content = disk.read_file(src)
                                ram.load(dst, content)
                                disk.write_file(dst, content)
                                print(f"Copied {src} to {dst}")

                            elif subcmd == "mkdir":
                                folder = get_abs_path(parts[1])
                                disk.mkdir(folder)

                            elif subcmd == "cd":
                                target = parts[1]
                                new_path = get_abs_path(target)
                                if disk.is_folder(new_path):
                                    current_dir = new_path

                            elif subcmd == "save":
                                disk.write_bulk(ram.memory)
                                print("RAM contents saved to disk.")

                            elif subcmd == "tree":
                                tree_command("/", disk)

                            elif subcmd == "ramload":
                                key = get_abs_path(parts[1])
                                value = " ".join(parts[2:])
                                ram.load(key, value)
                                print(f"Loaded into RAM: {key}")

                            elif subcmd == "ramclear":
                                ram.clear()
                                print("RAM cleared.")

                            elif subcmd == "ramshow":
                                if ram.memory:
                                    print("RAM contents:")
                                    for k,v in ram.memory.items():
                                        print(f"{k} : {v}")
                                else:
                                    print("RAM is empty.")

                            elif subcmd == "sysinfo":
                                cpu_info = cpu.get_info()
                                ram_info = ram.get_info()
                                disk_info = disk.get_info()
                                print("-" * 40)
                                print(f"CPU    : Cycles: {cpu_info['cycles']}")
                                print(f"RAM    : {ram_info['total_kb']} KB | Used: {ram_info['used_kb']} KB | Free: {ram_info['free_kb']} KB")
                                print(f"DISK   : {disk_info['max_kb']} KB | Used: {disk_info['used_kb']} KB | Free: {disk_info['free_kb']} KB | Files: {disk_info['file_count']}")
                                print("-" * 40)

                            elif subcmd == "reboot":
                                print("Saving RAM contents to Disk and rebooting...")
                                disk.write_bulk(ram.memory)
                                ram.clear()
                                boot()
                                return

                            elif subcmd == "format":
                                print("Unable to access.")

                            elif subcmd == "exit":
                                print("Exiting program...")
                                break

                            else:
                                print(f"[RUN] Unsupported command: {subcmd}")
#################################################end#######################################
            elif cmd == "dir":
                items = disk.list_dir(current_dir)
                if items:
                    for item in items:
                        item_path = current_dir.rstrip("/") + "/" + item if current_dir != "/" else "/" + item
                        if disk.is_folder(item_path):
                            print(f"<DIR> {item}")
                        else:
                            print(f"      {item}")
                else:
                    print("No files or directories.")

            elif cmd == "tree":
                tree_command(current_dir, disk)

            elif cmd == "write":
                if len(tokens) < 3:
                    print("Usage: WRITE filename content")
                else:
                    filename = get_abs_path(tokens[1])
                    content = " ".join(tokens[2:])
                    ram.load(filename, content)
                    disk.write_bulk(ram.memory)
                    disk.write_file(filename, content)
                    print(f"Written to RAM and Disk: {filename}")

            elif cmd == "type":
                if len(tokens) < 2:
                    print("Usage: TYPE filename")
                else:
                    filename = get_abs_path(tokens[1])
                    content = ram.get(filename)
                    if content is None:
                        content = disk.read_file(filename)
                    print(content)
            elif cmd == "print":
                if len(tokens) < 2:
                    print("Usage: PRINT text_to_print")
                else:
                    text = " ".join(tokens[1:])
                    print(text)
            elif cmd == "clearcpu":
                cpu.clearcpu()
                print("CPU cycles cleared to 0.")

            elif cmd == "del":
                if len(tokens) < 2:
                    print("Usage: DEL filename")
                else:
                    filename = get_abs_path(tokens[1])
                    ram.memory.pop(filename, None)
                    disk.delete_file(filename)
                    print(f"Deleted from RAM and Disk: {filename}")

            elif cmd == "copy":
                if len(tokens) < 3:
                    print("Usage: COPY source_file destination_file")
                else:
                    src = get_abs_path(tokens[1])
                    dst = get_abs_path(tokens[2])
                    content = ram.get(src)
                    if content is None:
                        content = disk.read_file(src)
                        if content == "[File not found]":
                            print(f"Source file '{src}' not found.")
                            continue
                    ram.load(dst, content)
                    disk.write_file(dst, content)
                    print(f"Copied '{src}' to '{dst}'.")

            elif cmd == "rename":
                if len(tokens) < 3:
                    print("Usage: RENAME old_filename new_filename")
                else:
                    old_name = get_abs_path(tokens[1])
                    new_name = get_abs_path(tokens[2])

                    content = ram.get(old_name)
                    if content is None:
                        content = disk.read_file(old_name)
                        if content == "[File not found]":
                            print(f"File '{old_name}' not found.")
                            continue
                    ram.memory.pop(old_name, None)
                    ram.load(new_name, content)

                    disk.delete_file(old_name)
                    disk.write_file(new_name, content)

                    print(f"Renamed '{old_name}' to '{new_name}'.")

            elif cmd == "ramload":
                if len(tokens) < 3:
                    print("Usage: RAMLOAD key value")
                else:
                    key = get_abs_path(tokens[1])
                    value = " ".join(tokens[2:])
                    ram.load(key, value)
                    print(f"Loaded into RAM: {key}")

            elif cmd == "ramclear":
                ram.clear()
                print("RAM cleared.")

            elif cmd == "ramshow":
                if ram.memory:
                    print("RAM contents:")
                    for k,v in ram.memory.items():
                        print(f"{k} : {v}")
                else:
                    print("RAM is empty.")

            elif cmd == "sysinfo":
                cpu_info = cpu.get_info()
                ram_info = ram.get_info()
                disk_info = disk.get_info()

                print("-" * 40)
                print(f"CPU    : Cycles: {cpu_info['cycles']}")
                print(f"RAM    : {ram_info['total_kb']} KB | Used: {ram_info['used_kb']} KB | Free: {ram_info['free_kb']} KB")
                print(f"DISK   : {disk_info['max_kb']} KB | Used: {disk_info['used_kb']} KB | Free: {disk_info['free_kb']} KB | Files: {disk_info['file_count']}")
                print("-" * 40)

            elif cmd == "reboot":
                print("Saving RAM contents to Disk and rebooting...")
                disk.write_bulk(ram.memory)
                ram.clear()
                time.sleep(0.1)
                boot()
                return

            elif cmd == "format":
                confirm = input("Are you sure you want to format the disk? (y/n): ").strip().lower()
                if confirm == "y":
                    disk.format_disk()
                    print("Disk formatted successfully.")
                elif confirm == "n":
                    print("Format cancelled.")
                else:
                    print("Invalid choice. Format aborted.")
            
            elif cmd == "help":
                print("=== PY-DOS HELP ===")
                print("DIR <path>            - List files and directories")
                print("TREE <path>           - Show directory tree")
                print("TYPE <file>           - Show file content")
                print("WRITE <file> <content> - Write content to a file (RAM+Disk)")
                print("DEL <file>            - Delete file from RAM and Disk")
                print("RENAME <old> <new>    - Rename a file")
                print("COPY <src> <dst>      - Copy a file")
                print("MKDIR <folder>        - Create directory")
                print("CD <folder> / CCD     - Change current directory")
                print("RUN <file>            - Run a script or application")
                print("SAVE                  - Save RAM contents to Disk")
                print("RAMLOAD <key> <value> - Load a value into RAM")
                print("RAMCLEAR              - Clear all RAM contents")
                print("RAMSHOW               - Display RAM contents")
                print("SYSINFO               - Show CPU, RAM, and Disk info")
                print("REBOOT                - Save RAM to disk and restart system")
                print("FORMAT                - Format the disk (confirmation required)")
                print("PRINT <text>          - Print text to screen")
                print("CLEARCPU              - Reset CPU cycles to 0")
                print("AMS                   - Run Anti-Malware Scan (disk & RAM)")
                print("EXIT                  - Exit PY-DOS")
            else:
                print("Bad command or file name.")

        except KeyboardInterrupt:
            print("\nUse EXIT to quit.")
        except Exception as e:
            print(f"[ERROR] {e}")

### --- Boot --- ###
def boot():
    print("PY-DOS v1.0 - Booting...")
    time.sleep(0.1)
    print("Initializing CPU...")
    cpu = CPU()
    print("Initializing RAM...")
    ram = RAM()
    time.sleep(0.05)
    print("Checking DISK...")
    disk = Disk()
    time.sleep(0.05)
    print("Boot successful.")
    start_terminal(cpu, ram, disk)

if __name__ == "__main__":
    boot()

