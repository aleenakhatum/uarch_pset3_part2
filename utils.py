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

def get_reg_val(state, index, size):
    # Map for 32-bit names
    reg_name = REG32[index] # e.g., "eax", "ecx"
    full_val = getattr(state, reg_name)
    
    if size == 4:
        return full_val & 0xFFFFFFFF
    if size == 2:
        return full_val & 0xFFFF
    if size == 1:
        # index 0-3 are AL, CL, DL, BL
        if index < 4:
            return full_val & 0xFF
        # index 4-7 are AH, CH, DH, BH (the second byte of EAX, ECX, etc.)
        else:
            return (getattr(state, REG32[index-4]) >> 8) & 0xFF
            
    return full_val

def write_reg_val(state, index, val, size):
    reg_name = REG32[index]
    current_val = getattr(state, reg_name)
    
    if size == 4:
        setattr(state, reg_name, val & 0xFFFFFFFF)
    elif size == 2:
        new_val = (current_val & 0xFFFF0000) | (val & 0xFFFF)
        setattr(state, reg_name, new_val)
    elif size == 1:
        if index < 4: # AL, CL, DL, BL
            new_val = (current_val & 0xFFFFFF00) | (val & 0xFF)
            setattr(state, reg_name, new_val)
        else: # AH, CH, DH, BH
            new_val = (current_val & 0xFFFF00FF) | ((val & 0xFF) << 8)
            setattr(state, REG32[index-4], new_val)

def read_mem(mem, addr, size):
    res = 0
    for i in range(size):
        res |= int(mem.get(addr + i, "00"), 16) << (8 * i)
    return res

def write_mem(mem, addr, val, size, state):
    """Writes to memory and tracks the address in state."""
    for i in range(size):
        phys_addr = addr + i
        mem[phys_addr] = f"{(val >> (8 * i)) & 0xFF:02X}"
        state.modified_mem.add(phys_addr)

def update_flags(flags, a, b, res, size, op="add"):
    #Reset
    flags["CF"] = 0
    flags["PF"] = 0
    flags["AF"] = 0
    flags["ZF"] = 0
    flags["SF"] = 0
    flags["DF"] = 0
    flags["OF"] = 0

    mask = (1 << (size * 8)) - 1
    sign_bit = 1 << (size * 8 - 1)
    
    # Ensure operands are masked to the current operation size
    a_m = a & mask
    b_m = b & mask
    res_m = res & mask
    print("resm", res_m)

    # Zero Flag
    flags["ZF"] = 1 if res_m == 0 else 0
    
    # Sign Flag
    flags["SF"] = 1 if (res_m & sign_bit) else 0

    if op == "add":
        # Carry Flag: Did the sum exceed the mask?
        flags["CF"] = 1 if res > mask else 0
        
        # Overflow Flag: (a and b have same sign) AND (result has different sign)
        # Using your logic but with the cleaned/masked operands:
        flags["OF"] = 1 if ((a_m ^ res_m) & (b_m ^ res_m) & sign_bit) else 0

    elif op == "sub" or op == "cmp":
        # Carry Flag for Subtraction is a "Borrow"
        flags["CF"] = 1 if a_m < b_m else 0
        
        # Overflow Flag for Subtraction
        flags["OF"] = 1 if ((a_m ^ b_m) & (a_m ^ res_m) & sign_bit) else 0
        
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
    

def write_results(state, mem, filename="results.txt"):
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