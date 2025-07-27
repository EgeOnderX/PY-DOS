### --- DISK --- ###
import os
import json

class Disk:
    def __init__(self, filename="disk.json", max_size_kb=512 * 1024):  # 512 MB
        self.filename = filename
        self.max_size_kb = max_size_kb
        if not os.path.exists(self.filename):
            self.format_disk()

    def format_disk(self):
        with open(self.filename, "w") as f:
            json.dump({}, f)

    def _load(self):
        with open(self.filename, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def _split_path(self, path):
        return [p for p in path.strip("/").split("/") if p]

    def _navigate(self, data, path_parts, create_missing=False):
        for part in path_parts[:-1]:
            if part not in data:
                if create_missing:
                    data[part] = {}
                else:
                    return None
            data = data[part]
            if not isinstance(data, dict):
                return None
        return data

    def write_file(self, filepath, content):
        data = self._load()
        path_parts = self._split_path(filepath)
        if not path_parts:
            print("[DISK] Invalid file path.")
            return
        parent = self._navigate(data, path_parts[:-1], create_missing=True)
        if parent is None:
            print("[DISK] Invalid path")
            return
        parent[path_parts[-1]] = content
        if self._get_used_space_kb(data) <= self.max_size_kb:
            self._save(data)
        else:
            print("[DISK] Not enough space! Write failed.")
            del parent[path_parts[-1]]

    def read_file(self, filepath):
        data = self._load()
        path_parts = self._split_path(filepath)
        if not path_parts:
            return "[File not found]"
        parent = data
        for part in path_parts[:-1]:
            if part in parent and isinstance(parent[part], dict):
                parent = parent[part]
            else:
                return "[File not found]"
        last_part = path_parts[-1]
        if last_part in parent:
            if isinstance(parent[last_part], dict):
                return "[Is a directory]"
            return parent[last_part]
        return "[File not found]"


    def delete_file(self, filepath):
        data = self._load()
        path_parts = self._split_path(filepath)
        if not path_parts:
            return
        parent = self._navigate(data, path_parts)
        if parent and path_parts[-1] in parent:
            del parent[path_parts[-1]]
            self._save(data)

    def mkdir(self, folder_path):
        data = self._load()
        path_parts = self._split_path(folder_path)
        if not path_parts:
            print("[DISK] Invalid folder path.")
            return
        parent = self._navigate(data, path_parts, create_missing=True)
        if parent is None:
            print("[DISK] Invalid path")
            return
        folder_name = path_parts[-1]
        if folder_name not in parent:
            parent[folder_name] = {}
            self._save(data)
        else:
            print("[DISK] Folder already exists")

    def list_dir(self, folder_path):
        data = self._load()
        path_parts = self._split_path(folder_path)
        if len(path_parts) == 0:
            parent = data
        else:
            parent = data
            for part in path_parts:
                if part in parent and isinstance(parent[part], dict):
                    parent = parent[part]
                else:
                    return []
        if isinstance(parent, dict):
            return list(parent.keys())
        return []


    def is_folder(self, path):
        data = self._load()
        path_parts = self._split_path(path)
        if len(path_parts) == 0:
            return True
        parent = data
        for part in path_parts[:-1]:
            if part in parent and isinstance(parent[part], dict):
                parent = parent[part]
            else:
                return False
        last = path_parts[-1]
        return isinstance(parent.get(last, None), dict)


    def _get_used_space_kb(self, data):
        def walk(d):
            total = 0
            for k, v in d.items():
                total += len(k.encode("utf-8"))
                if isinstance(v, dict):
                    total += walk(v)
                else:
                    total += len(v.encode("utf-8"))
            return total
        return walk(data) // 1024

    def get_info(self):
        data = self._load()
        used = self._get_used_space_kb(data)
        return {
            "max_kb": self.max_size_kb,
            "used_kb": used,
            "free_kb": self.max_size_kb - used,
            "file_count": self._count_files(data)
        }

    def _count_files(self, d):
        count = 0
        for v in d.values():
            if isinstance(v, dict):
                count += self._count_files(v)
            else:
                count += 1
        return count

    def get_structure(self):
        return self._load()

    def write_bulk(self, data_dict):
        data = self._load()

        for filepath, content in data_dict.items():
            path_parts = self._split_path(filepath)  
            if not path_parts:
                continue

            parent = data
            for part in path_parts[:-1]:
                if part not in parent or not isinstance(parent[part], dict):
                    parent[part] = {}
                parent = parent[part]
            parent[path_parts[-1]] = content
        if self._get_used_space_kb(data) <= self.max_size_kb: #umm sometimes works but... sometimes (always) not.
            self._save(data)
        else:
            print("[DISK] Not enough space! Bulk write failed.")

