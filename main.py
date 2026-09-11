import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VMS_DIR = os.path.join(BASE_DIR, "vms")
os.makedirs(VMS_DIR, exist_ok=True)


def _safe_name(name):
    name = name.strip()
    if not name:
        return ""
    invalid = '<>:"/\\|?*'
    return "".join("_" if ch in invalid else ch for ch in name)


def _find_vm_dir(vm_name):
    target = vm_name.strip().casefold()
    for entry in os.listdir(VMS_DIR):
        full = os.path.join(VMS_DIR, entry)
        if os.path.isdir(full) and entry.casefold() == target:
            return full
    return None


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def list_vms():
    result = []
    for entry in sorted(os.listdir(VMS_DIR), key=str.casefold):
        full = os.path.join(VMS_DIR, entry)
        if not os.path.isdir(full):
            continue
        cfg = _read_json(os.path.join(full, "config.json"), {})
        if isinstance(cfg, dict) and cfg.get("name"):
            result.append((entry, cfg))
    return result


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PY-DOS VM Manager")
        self.root.geometry("940x600")
        self.root.minsize(840, 520)

        self.selected_vm = None
        self.vars = {
            "name": tk.StringVar(),
            "disk_mb": tk.IntVar(value=512),
            "ram_mb": tk.IntVar(value=128),
            "version": tk.StringVar(value="1.0"),
        }

        self._build_ui()
        self.refresh_vm_list()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="PY-DOS Virtual Machine Manager", font=("TkDefaultFont", 16, "bold")).pack(side="left")

        ttk.Button(top, text="Create VM", command=self.create_vm).pack(side="right")
        ttk.Button(top, text="Refresh", command=self.refresh_vm_list).pack(side="right", padx=(0, 8))

        main = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main.pack(fill="both", expand=True)

        left = ttk.LabelFrame(main, text="Virtual Machines", padding=8)
        left.pack(side="left", fill="both", expand=False)

        self.vm_list = tk.Listbox(left, width=34, activestyle="dotbox")
        self.vm_list.pack(side="left", fill="both", expand=True)
        self.vm_list.bind("<<ListboxSelect>>", self.on_select)

        scroll = ttk.Scrollbar(left, orient="vertical", command=self.vm_list.yview)
        scroll.pack(side="right", fill="y")
        self.vm_list.configure(yscrollcommand=scroll.set)

        right = ttk.LabelFrame(main, text="VM Settings", padding=14)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        grid = ttk.Frame(right)
        grid.pack(fill="x")

        ttk.Label(grid, text="VM Name:").grid(row=0, column=0, sticky="w", pady=7)
        ttk.Entry(grid, textvariable=self.vars["name"], width=36).grid(row=0, column=1, sticky="ew", pady=7)

        ttk.Label(grid, text="Disk Size (MB):").grid(row=1, column=0, sticky="w", pady=7)
        ttk.Entry(grid, textvariable=self.vars["disk_mb"], width=36).grid(row=1, column=1, sticky="ew", pady=7)

        ttk.Label(grid, text="RAM Size (MB):").grid(row=2, column=0, sticky="w", pady=7)
        ttk.Entry(grid, textvariable=self.vars["ram_mb"], width=36).grid(row=2, column=1, sticky="ew", pady=7)

        ttk.Label(grid, text="PY-DOS Version:").grid(row=3, column=0, sticky="w", pady=7)
        ttk.Combobox(
            grid,
            textvariable=self.vars["version"],
            values=("1.0", "1.1", "2.0"),
            state="normal",
            width=33
        ).grid(row=3, column=1, sticky="ew", pady=7)

        grid.columnconfigure(1, weight=1)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=(18, 8))

        ttk.Button(btns, text="Save Changes", command=self.save_changes).pack(side="left")
        ttk.Button(btns, text="Edit Config", command=self.edit_config).pack(side="left", padx=8)
        ttk.Button(btns, text="Start VM", command=self.start_vm).pack(side="left")

        self.info = tk.Text(right, height=16, state="disabled", wrap="word", font=("Consolas", 10))
        self.info.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Label(
            self.root,
            text="VMs are stored in ./vms/<VM_NAME>/ with config.json and <VM_NAME>.pydos"
        ).pack(fill="x", padx=10, pady=(0, 10))

    def _set_info(self, text):
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", text)
        self.info.configure(state="disabled")

    def refresh_vm_list(self):
        self.vm_list.delete(0, "end")
        vms = list_vms()
        for folder, cfg in vms:
            name = cfg.get("name", folder)
            self.vm_list.insert("end", name)

        # İlk VM var ise otomatik olarak seçili gelsin
        if self.vm_list.size() > 0:
            self.vm_list.selection_set(0)
            self.on_select()
        else:
            self.selected_vm = None
            self.vars["name"].set("")
            self.vars["disk_mb"].set(512)
            self.vars["ram_mb"].set(128)
            self.vars["version"].set("1.0")
            self._set_info("Select a VM from the list.")

    def on_select(self, _event=None):
        selection = self.vm_list.curselection()
        if not selection:
            return

        name = self.vm_list.get(selection[0])
        vm_dir = _find_vm_dir(name)
        if not vm_dir:
            return

        self.selected_vm = vm_dir

        cfg = _read_json(os.path.join(vm_dir, "config.json"), {})
        self.vars["name"].set(cfg.get("name", os.path.basename(vm_dir)))
        self.vars["disk_mb"].set(int(cfg.get("disk_mb", 512)))
        self.vars["ram_mb"].set(int(cfg.get("ram_mb", 128)))
        self.vars["version"].set(str(cfg.get("version", "1.0")))

        disk_file = os.path.join(vm_dir, f"{cfg.get('name', os.path.basename(vm_dir))}.pydos")

        info = (
            f"VM folder : {vm_dir}\n"
            f"Disk file : {disk_file}\n"
            f"Config    : {os.path.join(vm_dir, 'config.json')}\n"
            f"Disk size : {cfg.get('disk_mb', 512)} MB\n"
            f"RAM size  : {cfg.get('ram_mb', 128)} MB\n"
            f"Version   : {cfg.get('version', '1.0')}\n"
        )

        self._set_info(info)

    def create_vm(self):
        dialog = VMDialog(self.root)
        self.root.wait_window(dialog.top)

        if not dialog.result:
            return

        name, disk_mb, ram_mb, version = dialog.result
        clean = _safe_name(name)

        if not clean:
            messagebox.showerror("Create VM", "VM name cannot be empty.")
            return

        if _find_vm_dir(clean):
            messagebox.showerror("Create VM", "A VM with this name already exists.")
            return

        vm_dir = os.path.join(VMS_DIR, clean)
        os.makedirs(vm_dir, exist_ok=True)

        cfg = {
            "name": name,
            "version": version,
            "disk_mb": disk_mb,
            "ram_mb": ram_mb,
            "disk_filename": f"{name}.pydos",
            "system_folder": None,
        }

        _write_json(os.path.join(vm_dir, "config.json"), cfg)

        _write_json(
            os.path.join(vm_dir, f"{name}.pydos"),
            {
                "__disk__": {
                    "format": "pydos",
                    "version": 1,
                    "capacity_kb": disk_mb * 1024
                }
            }
        )

        messagebox.showinfo("Create VM", f"VM '{name}' created.")
        self.refresh_vm_list()

    def save_changes(self):
        if not self.selected_vm:
            messagebox.showwarning("VM Manager", "Select a VM first.")
            return

        old_cfg = _read_json(os.path.join(self.selected_vm, "config.json"), {})
        old_name = old_cfg.get("name", os.path.basename(self.selected_vm))

        try:
            new_name = _safe_name(self.vars["name"].get())
            disk_mb = int(self.vars["disk_mb"].get())
            ram_mb = int(self.vars["ram_mb"].get())
            version = str(self.vars["version"].get()).strip()
        except (TypeError, ValueError):
            messagebox.showerror("VM Manager", "Disk and RAM must be numeric.")
            return

        if not new_name or disk_mb <= 0 or ram_mb <= 0:
            messagebox.showerror("VM Manager", "Name must be valid and sizes must be > 0.")
            return

        cfg = dict(old_cfg)
        cfg.update({
            "name": new_name,
            "version": version or "1.0",
            "disk_mb": disk_mb,
            "ram_mb": ram_mb,
            "disk_filename": f"{new_name}.pydos",
        })

        old_disk = os.path.join(self.selected_vm, f"{old_name}.pydos")
        new_disk = os.path.join(self.selected_vm, f"{new_name}.pydos")

        if os.path.isfile(old_disk) and old_disk != new_disk:
            if os.path.isfile(new_disk):
                messagebox.showerror("VM Manager", "Target disk filename already exists.")
                return
            os.replace(old_disk, new_disk)
        elif not os.path.isfile(new_disk):
            _write_json(
                new_disk,
                {
                    "__disk__": {
                        "format": "pydos",
                        "version": 1,
                        "capacity_kb": disk_mb * 1024
                    }
                }
            )

        _write_json(os.path.join(self.selected_vm, "config.json"), cfg)
        messagebox.showinfo("VM Manager", "Changes saved.")
        self.refresh_vm_list()

    def edit_config(self):
        if not self.selected_vm:
            messagebox.showwarning("VM Manager", "Select a VM first.")
            return

        path = os.path.join(self.selected_vm, "config.json")

        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror("Edit Config", str(exc))

    def start_vm(self):
        name = self.vars["name"].get().strip()

        if not name:
            messagebox.showwarning("VM Manager", "Select a VM first.")
            return

        vm_dir = self.selected_vm or _find_vm_dir(name)

        if not vm_dir:
            messagebox.showerror("VM Manager", "VM directory not found.")
            return

        try:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "vm.py"), name], cwd=BASE_DIR)
        except Exception as exc:
            messagebox.showerror("Start VM", str(exc))


class VMDialog:
    def __init__(self, parent):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Create VM")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)

        self.name = tk.StringVar(value="Ege")
        self.disk = tk.IntVar(value=512)
        self.ram = tk.IntVar(value=128)
        self.version = tk.StringVar(value="1.0")

        frm = ttk.Frame(self.top, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="VM Name").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.name, width=30).grid(row=0, column=1, pady=6)

        ttk.Label(frm, text="Disk Size (MB)").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.disk, width=30).grid(row=1, column=1, pady=6)

        ttk.Label(frm, text="RAM Size (MB)").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.ram, width=30).grid(row=2, column=1, pady=6)

        ttk.Label(frm, text="PY-DOS Version").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Combobox(frm, textvariable=self.version, values=("1.0", "1.1", "2.0"), width=27).grid(row=3, column=1, pady=6)

        actions = ttk.Frame(frm)
        actions.grid(row=4, column=0, columnspan=2, pady=(14, 0))

        ttk.Button(actions, text="Create", command=self.ok).pack(side="left")
        ttk.Button(actions, text="Cancel", command=self.top.destroy).pack(side="left", padx=8)

    def ok(self):
        try:
            disk = int(self.disk.get())
            ram = int(self.ram.get())
        except ValueError:
            messagebox.showerror("Create VM", "Disk and RAM must be numbers.", parent=self.top)
            return
    
        if not self.name.get().strip() or disk <= 0 or ram <= 0:
            messagebox.showerror("Create VM", "Invalid values.", parent=self.top)
            return

        self.result = (self.name.get().strip(), disk, ram, self.version.get().strip() or "1.0")
        self.top.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconname("PY-DOS VM Manager")
    except Exception:
        pass

    MainApp(root)
    root.mainloop()
