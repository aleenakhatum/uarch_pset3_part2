def load_mem_file(mem, mem_file):
    with open(mem_file, 'r') as f:
        hex_str = ""
        hex_part2 = ""
        cur_addr = None
        prev_addr_num = None
        broken_line = False
        prev_line = None
        for line in f:

            #Remove Comments / Whitespace
            l = line.split('//')[0].strip()
            if not l:
                continue #skip empty lines
            
            #Parse
            if l.startswith("0x"): #new address line
                addr_str, hex_str = l.split(":", 1) #split line once into two
                addr_num = int(addr_str, 16)
                prev_addr_num = addr_num
            else: #continuation of previous hex
                hex_str = l.strip()
                broken_line = True

            #Convert hex into bytes
            byte_list = hex_str.split()
            for i in byte_list:
                if broken_line:
                    break
                else:
                    mem[addr_num] = i
                    addr_num += 1
            
            if broken_line:
                count = 0
                for b in reversed(byte_list):
                    bytes_num = len(prev_line) 
                    blah = prev_addr_num + bytes_num + count
                    mem[prev_addr_num + bytes_num + count] = b
                    count += 1
                    broken_line = False
            prev_line = byte_list

            with open("mem_dump.txt", "w") as dump:
                for addr, byte in sorted(mem.items()):
                    dump.write(f"{addr:08X}: {byte}\n")

def read_mem_word(mem, addr, size):
    """Read a value from memory dictionary as integer (little-endian)."""
    bytes_ = []
    for i in range(size):
        b = mem.get(addr + i, "00")
        bytes_.append(int(b, 16))
    return int.from_bytes(bytes_, "little")

def write_mem_word(mem, addr, value, size):
    """Write integer value into memory (little-endian)."""
    b = value.to_bytes(size, "little")
    for i in range(size):
        mem[addr + i] = f"{b[i]:02X}"

def read8(mem, addr):
    value = int(mem.get(addr, "00"), 16)   # get byte or default 0
    return value & 0xFF


def read16(mem, addr):
    b0 = int(mem.get(addr, "00"), 16)
    b1 = int(mem.get(addr + 1, "00"), 16)
    return (b1 << 8) | b0

def read32(mem, addr):
    b0 = int(mem.get(addr, "00"), 16)
    b1 = int(mem.get(addr + 1, "00"), 16)
    b2 = int(mem.get(addr + 2, "00"), 16)
    b3 = int(mem.get(addr + 3, "00"), 16)

    return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0

def write8(mem, addr, val):
    mem[addr] = f"{val & 0xFF:02X}"

def write16(mem, addr, val):
    write8(mem, addr, val)
    write8(mem, addr + 1, val >> 8)

def write32(mem, addr, val):
    write8(mem, addr, val)
    write8(mem, addr + 1, val >> 8)
    write8(mem, addr + 2, val >> 16)
    write8(mem, addr + 3, val >> 24)



                
