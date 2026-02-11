# utils.py

REG32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
REG8  = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]
SREGS = ["es", "cs", "ss", "ds", "fs", "gs"]

def sext(value, bits):
    """Sign extend value from 'bits' to 32 bits."""
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def decode_modrm(modrm_byte):
    mod = (modrm_byte >> 6) & 0b11
    reg = (modrm_byte >> 3) & 0b111
    rm  = modrm_byte & 0b111
    return mod, reg, rm

def get_reg_val(state, reg_idx, size):
    # Standard x86 GPR mapping
    names = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
    reg_name = names[reg_idx]
    
    # Use getattr to pull the value from the class attribute (e.g., state.eax)
    val = getattr(state, reg_name)

    if size == 1:
        return val & 0xFF        # AL, CL, DL, BL...
    if size == 2:
        return val & 0xFFFF      # AX, CX, DX, BX...
    return val & 0xFFFFFFFF      # EAX, ECX, EDX, EBX...

def write_reg_val(state, reg_idx, val, size):
    names = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
    reg_name = names[reg_idx]
    
    if size == 4:
        setattr(state, reg_name, val & 0xFFFFFFFF)
    elif size == 2:
        # Preserve upper 16 bits of the 32-bit register
        current = getattr(state, reg_name)
        new_val = (current & 0xFFFF0000) | (val & 0xFFFF)
        setattr(state, reg_name, new_val)
    elif size == 1:
        # Preserve upper 24 bits
        current = getattr(state, reg_name)
        new_val = (current & 0xFFFFFF00) | (val & 0xFF)
        setattr(state, reg_name, new_val)
        
def read_mem(mem, addr, size):
    res = 0
    for i in range(size):
        current_addr = addr + i
        
        # If the address is missing, initialize it to "00"
        if current_addr not in mem:
            mem[current_addr] = "00"
            
        # Get the value (now guaranteed to exist)
        val_str = mem[current_addr]
        
        # Convert hex string to int and shift it into the correct byte position
        res |= int(val_str, 16) << (8 * i)
        
    return res

def write_mem(mem, addr, val, size, state):
    """Writes to memory and tracks the address in state."""
    for i in range(size):
        phys_addr = addr + i
        mem[phys_addr] = f"{(val >> (8 * i)) & 0xFF:02X}"
        state.modified_mem.add(phys_addr)

def update_flags(flags, a, b, res, size, op="add"):
    # 1. Setup Masks
    mask = (1 << (size * 8)) - 1
    sign_bit = 1 << (size * 8 - 1)
    
    a_m = a & mask
    b_m = b & mask
    res_m = res & mask

    flags["ZF"] = 1 if res_m == 0 else 0
    flags["SF"] = 1 if (res_m & sign_bit) else 0

    lsb = res_m & 0xFF
    flags["PF"] = 1 if (bin(lsb).count('1') % 2 == 0) else 0

    flags["AF"] = 1 if ((a_m ^ b_m ^ res_m) & 0x10) else 0

    if op == "add":
        flags["CF"] = 1 if res_m < a_m else 0 # Or: (res > mask)
        
        flags["OF"] = 1 if ((a_m ^ res_m) & (b_m ^ res_m) & sign_bit) else 0

    elif op == "sub" or op == "cmp":
        flags["CF"] = 1 if a_m < b_m else 0
        flags["OF"] = 1 if ((a_m ^ b_m) & (a_m ^ res_m) & sign_bit) else 0
    
    return flags

def get_segment_for_instr(rm_index, prefix_mux, state):
    """
    Determines which segment register to use based on the base register 
    and segment override prefixes.
    """
    # 1. Check for Segment Override Prefix (prefix_mux[0])
    # Note: If your decoder stores the specific override (e.g., 0x26 for ES), 
    # you would use that. For this assignment, we simplify.
    
    # 2. Check for Stack-based access (EBP is index 5, ESP is index 4)
    # If rm is 4 (ESP) or 5 (EBP), use SS. Otherwise use DS.
    if rm_index in (4, 5):
        return state.ss
    else:
        return state.ds

def calc_effective_addr(instr, state):
    """
    Computes: [Base + Displacement + (Segment << 16)]
    Supports ModR/M Base+Displacement (no SIB).
    """
    mod, reg, rm = decode_modrm(instr.modrm)
    
    # Get the base register value
    # Case: mod 00, rm 101 is Displacement-only (disp32) in x86
    if mod == 0b00 and rm == 0b101:
        base_val = 0
    else:
        base_reg_name = REG32[rm]
        base_val = getattr(state, base_reg_name)

    # Displacement logic based on Mod
    disp = 0
    if mod == 0b01:   # 8-bit displacement
        disp = sext(instr.disp, 8)
    elif mod == 0b10: # 32-bit displacement
        disp = instr.disp
    elif mod == 0b00 and rm == 0b101: # Absolute 32-bit disp
        disp = instr.disp

    # Segment selection
    seg_val = get_segment_for_instr(rm, instr.prefix_mux, state)
    
    # Final 32-bit Address Calculation
    eff_addr = (base_val + disp + (seg_val << 16)) & 0xFFFFFFFF
    return eff_addr

def get_operand_size(opcode, prefix_mux):
    """
    Returns the size in bytes (1, 2, or 4).
    Uses the 0x66 bit (prefix_mux[1]) to toggle between 16 and 32 bits.
    """
    # Group 1: 8-bit opcodes (usually even numbers or specific ranges)
    # Examples: 0x00 (ADD r/m8, r8), 0x04 (ADD AL, imm8), 0x80 (ADD r/m8, imm8)
    if opcode in (0x00, 0x02, 0x04, 0x80, 0x86):
        return 1
    
    # Group 2: Toggle-able opcodes (16 or 32 bit)
    # Check bit index 1 of your prefix_mux
    if prefix_mux[1] == 1:
        return 2  # 16-bit (Word)
    else:
        return 4  # 32-bit (Double Word)
    

def write_results1(state, mem, filename="results.txt"):
    """
    Formats the CPU state and modified memory into a clear, tabular view.
    Appends to results.txt.
    """
    with open(filename, "a") as f:
        f.write(f"--- Instruction Executed. New State: ---\n")
        f.write(f"EIP : 0x{state.eip:08X}\n\n")

        # General Purpose Registers
        f.write("General Purpose Registers:\n")
        f.write(f"  EAX: {state.eax:08X}   EBX: {state.ebx:08X}   ECX: {state.ecx:08X}   EDX: {state.edx:08X}\n")
        f.write(f"  ESP: {state.esp:08X}   EBP: {state.ebp:08X}   ESI: {state.esi:08X}   EDI: {state.edi:08X}\n\n")

        # MMX Registers (64-bit)
        f.write("MMX Registers:\n")
        f.write(f"  MM0: {state.mm0:016X}   MM1: {state.mm1:016X}\n")
        f.write(f"  MM2: {state.mm2:016X}   MM3: {state.mm3:016X}\n")
        f.write(f"  MM4: {state.mm4:016X}   MM5: {state.mm5:016X}\n")
        f.write(f"  MM6: {state.mm6:016X}   MM7: {state.mm7:016X}\n\n")

        # Segment Registers and Flags
        f.write("Segment Registers:           Flags:\n")
        flag_str = " ".join([f"{k}:{v}" for k, v in state.flags.items()])
        f.write(f"  CS: {state.cs:04X}  DS: {state.ds:04X}  SS: {state.ss:04X}    {flag_str}\n")
        f.write(f"  ES: {state.es:04X}  FS: {state.fs:04X}  GS: {state.gs:04X}\n\n")

        # Sparse Memory Section
        f.write("Modified Memory Locations:\n")
        if not state.modified_mem:
            f.write("  (No memory writes yet)\n")
        else:
            # Sort addresses for readability and group into 4-byte rows
            sorted_addrs = sorted(list(state.modified_mem))
            printed_rows = set()
            
            for addr in sorted_addrs:
                # Align to 4-byte boundary (e.g., 0x1001 -> 0x1000)
                base_addr = addr & ~0x3
                if base_addr in printed_rows:
                    continue
                
                # Build the hex string for the 4-byte block
                bytes_str = ""
                for i in range(4):
                    bytes_str += f"{mem.get(base_addr + i, '00')} "
                
                f.write(f"  [0x{base_addr:04X}]: {bytes_str.strip()}\n")
                printed_rows.add(base_addr)
        
        f.write("\n" + "="*60 + "\n\n")

def write_results(state, mem, filename="results.txt"):
    """
    Formats the CPU state and modified memory into the requested compact view.
    Appends to results.txt.
    """
    with open(filename, "a") as f:
        # Instruction Pointer
        f.write(f"EIP: {state.eip:08X}\n")

        # General Purpose Registers
        f.write(f"EAX: {state.eax:08X} EBX: {state.ebx:08X} ECX: {state.ecx:08X} EDX: {state.edx:08X}\n")
        f.write(f"ESP: {state.esp:08X} EBP: {state.ebp:08X} ESI: {state.esi:08X} EDI: {state.edi:08X}\n")

        # MMX Registers (All on one line as requested)
        mm_regs = [
            f"MM0:{state.mm0:016X}", f"MM1:{state.mm1:016X}", f"MM2:{state.mm2:016X}", f"MM3:{state.mm3:016X}",
            f"MM4:{state.mm4:016X}", f"MM5:{state.mm5:016X}", f"MM6:{state.mm6:016X}", f"MM7:{state.mm7:016X}"
        ]
        f.write(" ".join(mm_regs) + "\n")

        # Segment Registers
        f.write(f"CS: {state.cs:04X} DS: {state.ds:04X} ES: {state.es:04X} FS: {state.fs:04X} GS: {state.gs:04X} SS: {state.ss:04X}\n")

        # Individual Flags
        flags = state.flags
        f.write(f"CF:{flags['CF']} PF:{flags['PF']} AF:{flags['AF']} ZF:{flags['ZF']} SF:{flags['SF']} DF:{flags['DF']} OF:{flags['OF']}\n")
        
        f.write("-" * 20 + "\n")

        # Memory Section
        f.write("Memory:\n")
        if not mem:
            f.write("  (No memory data)\n")
        else:
            sorted_addrs = sorted(mem.keys())
            m_str = ""
            for i, addr in enumerate(sorted_addrs):
                val = mem[addr]
                
                # If it's a string, convert from hex (base 16)
                # If it's already an int, use it directly
                if isinstance(val, str):
                    val_int = int(val, 16) 
                else:
                    val_int = val
                
                m_str += f"{addr:8X}: {val_int:02X}   "
                
                if (i + 1) % 4 == 0:
                    m_str += "\n"
            
            f.write(m_str.rstrip() + "\n\n")