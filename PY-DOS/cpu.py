class CPU:
    def __init__(self):
        self.cycles = 0

    def execute(self, command):
        self.cycles += 1
        print(f"[CPU] Processing command: {command}")
        return command.split()

    def get_info(self):
        return {
            "cycles": self.cycles
        }

    def clearcpu(self):
        self.cycles = 0
