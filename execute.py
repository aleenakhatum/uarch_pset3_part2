from instr_class import *
from utils import *
from memory import *

# raw opcode groups
ADD_OPCODES = (0x04, 0x05, 0x80, 0x81, 0x83, 0x00, 0x01, 0x02, 0x03)

# Added 0xB0-0xBF (MOV reg, imm) and 0xC6-0xC7 (MOV r/m, imm)
MOV_OPCODES = (
    0x6F, 0x8E, 0x88, 0x89, 0x8A, 0x8B, 
    0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 
    0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF,
    0xC6, 0xC7
)

XCHG_OPCODE = 0x86
CMPXCHG_OPCODE = 0xB1 # CMPXCHG is usually 0x0F 0xB1
JMP_OPCODE = 0xEA
JNE_OPCODE = 0x75 # Your test case uses 0x75 (JNE short)
HLT_OPCODE = 0xF4

def exec_ADD(instr, state, mem):
    op = instr.opcode
    size = get_operand_size(op, instr.prefix_mux)
    mod, reg, rm = decode_modrm(instr.modrm) if instr.modrm is not None else (0,0,0)

    # 1. Identify Source and Destination values
    if op in (0x04, 0x05): # ADD AL/EAX, imm
        dest_val = get_reg_val(state, 0, size)
        src_val = instr.imm
        dest_is_reg, dest_idx = True, 0
    elif op in (0x80, 0x81, 0x83): # ADD r/m, imm
        addr = None if mod == 0b11 else calc_effective_addr(instr, state)
        dest_val = get_reg_val(state, rm, size) if mod == 0b11 else read_mem(mem, addr, size)
        # Fix: Ensure sign extension matches the destination size
        src_val = sext(instr.imm, 8) if op == 0x83 else instr.imm
        dest_is_reg, dest_idx = (True, rm) if mod == 0b11 else (False, addr)
    elif op in (0x00, 0x01): # ADD r/m, r
        addr = None if mod == 0b11 else calc_effective_addr(instr, state)
        dest_val = get_reg_val(state, rm, size) if mod == 0b11 else read_mem(mem, addr, size)
        src_val = get_reg_val(state, reg, size)
        dest_is_reg, dest_idx = (True, rm) if mod == 0b11 else (False, addr)
    elif op in (0x02, 0x03): # ADD r, r/m
        addr = None if mod == 0b11 else calc_effective_addr(instr, state)
        dest_val = get_reg_val(state, reg, size)
        src_val = get_reg_val(state, rm, size) if mod == 0b11 else read_mem(mem, addr, size)
        dest_is_reg, dest_idx = True, reg
    else:
        return 

    # 2. Compute result and update flags
    # IMPORTANT: Keep 'result' unmasked here so update_flags can see the carry
    result = dest_val + src_val
    update_flags(state.flags, dest_val, src_val, result, size, "add")

    # 3. Writeback (Masking happens HERE)
    mask = (1 << (size * 8)) - 1
    final_result = result & mask
    
    if dest_is_reg:
        write_reg_val(state, dest_idx, final_result, size)
    else:
        write_mem(mem, dest_idx, final_result, size, state)
    
    state.eip = instr.eip_new
    
def exec_MOV(instr, state, mem):
    op = instr.opcode
    size = get_operand_size(op, instr.prefix_mux)
    
    # Variant 1: MOV reg, imm (0xB0 - 0xBF)
    if 0xB0 <= op <= 0xBF:
        reg_idx = op & 0x07
        # 0xB0-0xB7 are 8-bit, 0xB8-0xBF are 16/32-bit
        actual_size = 1 if op <= 0xB7 else size
        write_reg_val(state, reg_idx, instr.imm, actual_size)

    # Variant 2: MOV r/m, imm (0xC6, 0xC7)
    elif op in (0xC6, 0xC7):
        mod, reg, rm = decode_modrm(instr.modrm)
        if mod == 0b11:
            write_reg_val(state, rm, instr.imm, size)
        else:
            addr = calc_effective_addr(instr, state)
            write_mem(mem, addr, instr.imm, size, state)

    # Variant 3: Segment Registers (0x8E)
    elif op == 0x8E:
        mod, reg, rm = decode_modrm(instr.modrm)
        val = get_reg_val(state, rm, 2) if mod == 0b11 else read_mem(mem, calc_effective_addr(instr, state), 2)
        sreg_names = ["es", "cs", "ss", "ds", "fs", "gs"]
        setattr(state, sreg_names[reg % 6], val)

    # Variant 4: MMX MOVQ (0x6F)
    elif op == 0x6F:
        mod, reg, rm = decode_modrm(instr.modrm)
        val = getattr(state, f"mm{rm}") if mod == 0b11 else read_mem(mem, calc_effective_addr(instr, state), 8)
        setattr(state, f"mm{reg}", val)

    state.eip = instr.eip_new

def exec_XCHG(instr, state, mem):
    # Assignment specifies XCHG r/m8, r8 (0x86)
    mod, reg, rm = decode_modrm(instr.modrm)
    val_r = get_reg_val(state, reg, 1)
    
    if mod == 0b11:
        val_rm = get_reg_val(state, rm, 1)
        write_reg_val(state, rm, val_r, 1)
    else:
        addr = calc_effective_addr(instr, state)
        val_rm = read_mem(mem, addr, 1)
        write_mem(mem, addr, val_r, 1, state)
        
    write_reg_val(state, reg, val_rm, 1)
    state.eip = instr.eip_new

def exec_CMPXCHG(instr, state, mem):
    # 1. Decode operands
    mod, reg, rm = decode_modrm(instr.modrm)
    # Note: 0xB0 is 8-bit, 0xB1 is 16/32-bit. Ensure size is handled.
    size = get_operand_size(instr.opcode, instr.prefix_mux) 
    
    # 2. Get values
    # Accumulator is index 0 (AL/AX/EAX)
    acc_val = get_reg_val(state, 0, size)
    
    addr = None if mod == 0b11 else calc_effective_addr(instr, state)
    dest_val = get_reg_val(state, rm, size) if mod == 0b11 else read_mem(mem, addr, size)
    src_val = get_reg_val(state, reg, size)

    # 3. Perform Comparison for Flags
    # CMPXCHG flags are set as if a CMP (subtraction) occurred: acc_val - dest_val
    temp_res = acc_val - dest_val

    # This will set ZF=1 if (acc_val - dest_val) & 0xFFFF == 0
    update_flags(state.flags, acc_val, dest_val, temp_res, size, op="sub")
    update_flags(state.flags, acc_val, dest_val, temp_res, size, op="sub")

    # 4. Conditional Exchange
    if acc_val == dest_val:
        # ZF is already set to 1 by update_flags because result is 0
        if mod == 0b11:
            write_reg_val(state, rm, src_val, size)
        else:
            write_mem(mem, addr, src_val, size, state)
    else:
        # ZF is already 0. Load destination into accumulator.
        write_reg_val(state, 0, dest_val, size) 

    state.eip = instr.eip_new

def exec_JMP(instr, state, mem):
    # JMP ptr16:32 (EA) - Far Jump
    # This jump sets both CS and EIP. 
    # Your decoder should have extracted the 6 bytes: [4 bytes offset][2 bytes selector]
    # Assuming your decoder put the 32-bit offset in instr.imm and selector in instr.disp
    state.eip = instr.imm
    state.cs = instr.disp & 0xFFFF

def exec_JNE(instr, state, mem):
    # Test case uses 0x75 (short jump). 
    # If ZF is 0, add sign-extended displacement to EIP
    if state.flags["ZF"] == 0:
        # If your decoder already put the jump target in instr.imm:
        state.eip = (instr.eip_new + sext(instr.imm, 8)) & 0xFFFFFFFF
    else:
        state.eip = instr.eip_new

def exec_HLT(instr, state, mem):
    print("hlt")
    state.halted = True

def execute(instr, state, mem):
    op = instr.opcode
    match op:
        case _ if op in ADD_OPCODES:
            exec_ADD(instr, state, mem)

        case _ if op == CMPXCHG_OPCODE and instr.ext_opcode == 1:
            exec_CMPXCHG(instr, state, mem)

        case _ if op in MOV_OPCODES:
            exec_MOV(instr, state, mem)

        case _ if op == XCHG_OPCODE:
            exec_XCHG(instr, state, mem)

        case _ if op == JMP_OPCODE:
            exec_JMP(instr, state, mem)

        case _ if op == JNE_OPCODE:
            exec_JNE(instr, state, mem)

        case _ if op == HLT_OPCODE:
            exec_HLT(instr, state, mem)