# registers.py

class Registers:
    def __init__(self):
        # Program counter
        self.eip = 0

        # General Purpose Registers (32-bit)
        self.eax = 0
        self.ecx = 0
        self.edx = 0
        self.ebx = 0
        self.esp = 0
        self.ebp = 0
        self.esi = 0
        self.edi = 0

        # Segment registers (16-bit)
        self.cs = 0
        self.ds = 0
        self.es = 0
        self.ss = 0
        self.fs = 0
        self.gs = 0

        # MMX registers (64-bit)
        self.mm0 = 0
        self.mm1 = 0
        self.mm2 = 0
        self.mm3 = 0
        self.mm4 = 0
        self.mm5 = 0
        self.mm6 = 0
        self.mm7 = 0

        # Flags stored as a dict for clarity
        self.flags = {
            "CF": 0,
            "PF": 0,
            "AF": 0,
            "ZF": 0,
            "SF": 0,
            "DF": 0,
            "OF": 0
        }

        self.modified_mem = set()

    # Optional: helper for 8-bit register names
    def read32(self, name):
        return getattr(self, name)

    def write32(self, name, val):
        setattr(self, name, val & 0xFFFFFFFF)

    # Optional: dump for debugging
    def dump(self):
        print("EIP =", hex(self.eip))
        print("EAX =", hex(self.eax), "EBX =", hex(self.ebx))
        print("ECX =", hex(self.ecx), "EDX =", hex(self.edx))
        print("ESP =", hex(self.esp), "EBP =", hex(self.ebp))
        print("ESI =", hex(self.esi), "EDI =", hex(self.edi))
        print("MM =", [hex(x) for x in self.mm])
        print("Flags =", self.flags)
