import time, sys, json, os, ram, disk, cpu
from cpu import CPU
from ram import RAM
from disk import Disk

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

            if not tokens:
                continue

            cmd = tokens[0].lower()

            if cmd == "exit":
                print("Exiting PY-DOS...")
                break

            elif cmd == "mkdir":
                if len(tokens) < 2:
                    print("Usage: MKDIR foldername")
                else:
                    folder_path = get_abs_path(tokens[1])
                    disk.mkdir(folder_path)

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
                print("Available commands:")
                print("DIR                - List files and directories")
                print("TYPE file          - Show file content")
                print("WRITE file content - Write file")
                print("DEL file           - Delete file")
                print("RENAME old new     - Rename file")
                print("COPY src dst       - Copy file")
                print("MKDIR folder       - Create directory")
                print("CD folder          - Change directory")
                print("TREE               - Show directory tree")
                print("RAMLOAD k v        - Load key-value into RAM")
                print("RAMCLEAR           - Clear RAM")
                print("RAMSHOW            - Show RAM contents")
                print("SYSINFO            - Show system info")
                print("REBOOT             - Save RAM to disk and reboot")
                print("FORMAT             - Format disk")
                print("EXIT               - Exit PY-DOS")

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
    time.sleep(0.05)
    print("Initializing RAM...")
    ram = RAM()
    time.sleep(0.05)
    print("Checking DISK...")
    disk = Disk()
    time.sleep(0.05)
    print("Boot successful.")
    time.sleep(0.1)
    start_terminal(cpu, ram, disk)

if __name__ == "__main__":
    boot()
