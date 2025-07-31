class RAM:
    def __init__(self, size_kb=128 * 1024):  # 128 MB
        self.size_kb = size_kb
        self.memory = {}

    def load(self, key, value):
        if len(self.memory) < (self.size_kb * 1024):
            self.memory[key] = value
        else:
            print("[RAM] Not enough memory!")

    def get(self, key):
        return self.memory.get(key, None)

    def clear(self):
        self.memory = {}

    def get_info(self):
        return {
            "total_kb": self.size_kb,
            "used_kb": len(self.memory),
            "free_kb": self.size_kb - len(self.memory)
        }
