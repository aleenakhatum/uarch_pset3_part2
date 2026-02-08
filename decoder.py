from instr_class import *

#Testbench Tools: Pass in a hex string with spaces between every 2 hex characters (between every byte) OR a continuous hex string
def format_instr_in(instr_str, spaces):
    instr_bytes = () #empty list
    if (spaces):
        instr_bytes = list(bytes.fromhex(instr_str))
    else: #continuous string passed in
        instr_bytes = [int(instr_str[i:i+2], 16) for i in range(0, len(instr_str), 2)]
    return instr_bytes


def is_prefix(byte): 
    return byte in {0xF3, #rep
                    0x66, #segment register override
                    0x26, 0x2E, 0x36, 0x3E, 0x64, 0x65,} #operand size override

#Opcode input into the function should not contain 0x0F byte and should only contain the main byte of the opcode
def needs_modrm(opcode, ext_opcode):
     modrm_list_single = (0x00, 0x01, 0x02, 0x03, 0x08, 0x09, 0x0A, 0x0B, 0x20, 0x21, 0x22, 0x23, 0x80, 0x81, 0x83, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8E, 0x8F, 0xC0, 0xC1, 0xC6, 0xC7, 0xD0, 0xD1, 0xD2, 0xD3, 0xF6, 0xF7, 0xFF)
     modrm_list_double = (0x42, 0x63, 0x6B, 0x68, 0x69, 0x6F, 0x7F, 0xB0, 0xB1, 0xBC, 0xFD, 0xFE)
     if (ext_opcode == 1): #indicates a 2 byte opcode 
         return opcode in modrm_list_double
     else: #indicates a single byte opcode
        return opcode in modrm_list_single

"""Returns a boolean on whether a certain opcode uses the SIB byte"""
def needs_sib(modrm, reg0_mux):
    mod = (modrm >> 6) & 0b11      # bits [7:6]
    reg = (modrm >> 3) & 0b111     # bits [5:3]
    rm  = modrm & 0b111            # bits [2:0]

    if (rm == 0b100) and (mod != 0b11): #indicates presence of SIB byte
        reg0_mux[0] = 0b10
        return True
    else:
        return False

"""Returns displacement size in bytes (0, 1, 4) for a given modrm for some opcode"""
def disp_bytes(modrm, sib_byte):
    mod = (modrm >> 6) & 0b11      # bits [7:6]
    rm  = modrm & 0b111            # bits [2:0]
    sib = sib_byte & 0x07

    if mod == 0b01:
        return 1      # disp8
    if mod == 0b10 or (mod == 0b00 and sib == 0b101) or (mod == 0b00 and rm == 0b101):
        return 4      # disp32
    if mod == 0b00 and rm == 0b101:
        return 4      # disp32
    return 0          # no displacement

"""Returns immediate size in bytes (0, 1, 2, 4) for a given opcode"""
def imm_bytes(opcode, ext_opcode, operand_size_prefix, imm_type):

    #Use to update imm_type list object
    IMM_REGULAR = 0b00
    IMM_REL     = 0b01
    IMM_DOUBLE  = 0b10
    IMM_UNUSED  = 0b11
    imm_type[0] = IMM_REGULAR

    #Handles 2-byte opcode
    if (ext_opcode == 1):
        if opcode in (0x85, 0x87): #2 vs 4 byte immediate with operand_size_prefix
            imm_type[0] = IMM_REL
            if (operand_size_prefix == 1): #override (default is 32, override is 16)
                return 2 #cw next to opcode in instruction sheet
            else:
                return 4 #cd next to opcode in instruction sheet


    #Handles 1-byte opcode
    else:
        if (opcode & 0xF8 == 0xB0): #retrive base opcode range for 1 byte immediate
            return 1
        elif (opcode & 0xF8 == 0xB8): #retrieve base opcode range for 2 byte imediate
            if (operand_size_prefix == 1): #override (default is 32, override is 16)
                return 2 #cw next to opcode in instruction sheet
            else:
                return 4 #cd next to opcode in instruction sheet
            
        elif opcode in (0x04, 0x0C, 0x24, 0x6A, 0x75, 0x77, 0x80, 0x83, 0xB0, 0xC0, 0xC1, 0xC6, 0xEB): #1 byte immediate
            #Update Immediate Type
            if opcode in (0x75, 0x77, 0xEB):
                imm_type[0] = IMM_REL
            return 1
        elif opcode in (0xC2, 0xCA): #2 byte immediate
            return 2
        elif opcode in (0x05, 0x0D, 0x25, 0x68, 0x81, 0xC7, 0xE8, 0xE9): #either 2 byte or 4 byte immediate depending on prefix
            #Update Immediate Type
            if opcode in (0xE8, 0xE9):
                imm_type[0] = IMM_REL
            
            #Choose operand size
            if (operand_size_prefix == 1): #override (default is 32, override is 16)
                return 2 #cw next to opcode in instruction sheet
            else:
                return 4 #cd next to opcode in instruction sheet
        elif opcode in (0x9A, 0xEA): #double immediate instruction
            imm_type[0] = IMM_DOUBLE
            if (operand_size_prefix == 1 and opcode == 0xEA): #tells the size of the 2nd operand bc in all cases it is 16 bits for first operand
                return 2
            else: 
                return 4
    
def predecode(instr_str, eip, instr_cnt, dump_file=None):

    #Initialize all Ouput Registers
    if isinstance(instr_str, (bytes, bytearray)):
        has_spaces = False  # bytes never contain spaces
    else:
        has_spaces = " " in instr_str

    instr = format_instr_in(instr_str, has_spaces) #Autodetect if test has spaces
    prefix_mux = [0, 0, 0] 
    ext_opcode = 0
    opcode = 0x00 #byte
    modrm = 0x00 #byte
    sib = 0x00 #byte
    disp = 0x0000 #4 bytes
    disp_size_mux = 0 #32 bit or all 0 if 0, 8 bit if 1
    imm = 0x0000 #4 bytes
    imm_size_mux = 0 #8, 16, 32, unused (2 bits)
    eip_new = 0x00 #4 bytes
    reg0_mux = [0b00]; #zero val, modrm[2:0], sib[2:0], unused (2 bits)
    imm_type = [0] #placeholder value will be modified in imm_bytes

    #Parse Prefixes
    i = eip #index to access current part of instruction
    length = 1
    while (i < len(instr)):
        if (is_prefix(instr[i]) == False): #Iterate only as long as there are prefixes
            break
        prefix = instr[i]
        if prefix in (0xF3,): prefix_mux[2] = 1 #rep
        if prefix in (0x66,): prefix_mux[1] = 1 #operand size override
        if prefix in (0x26, 0x2E, 0x36, 0x3E, 0x64, 0x65): prefix_mux[0] = 1 #segment register override
        i += 1    
        length += 1    

    #Parse Opcode
    if (instr[i] == 0x0F):
        ext_opcode = 1
        i += 1
        length += 1
    opcode = instr[i]
    i += 1

    #Parse MODRM
    if (needs_modrm(opcode, ext_opcode)):
        modrm = instr[i]
        i += 1
        length += 1
        reg0_mux[0] = 0b01 #indicates modrm
    else:  
        modrm = 0x0

    #Parse SIB
    if (needs_sib(modrm, reg0_mux)):
        sib = instr[i]
        i += 1
        length += 1
    else:
        sib = 0x0

    #Parse Displacement
    disp_size = disp_bytes(modrm, sib)
    if (disp_size == 1):
        disp_size_mux = 1
        b0 = instr[i]
        disp = b0 & 0xFF
        i += 1
        length += 1
    elif (disp_size == 4):
        print("i", i)
        b0 = instr[i]
        i += 1
        length += 1
        b1 = instr[i]
        i += 1
        length += 1
        b2 = instr[i]
        i += 1
        length += 1
        b3 = instr[i]
        i += 1
        length += 1
        disp = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24) #little endian

    #Parse Immediate
    imm_size = imm_bytes(opcode, ext_opcode, prefix_mux[1], imm_type)
    if (imm_size == 0):
        imm = 0x0
    elif (imm_size == 1):
        imm_size_mux = 0b00 #1 byte
        b0 = instr[i]
        imm = b0 & 0xFF
        i += 1
        length += 1
    elif (imm_size == 2):
        imm_size_mux = 0b01 #2 bytes
        b0 = instr[i]
        i += 1
        length += 1
        b1 = instr[i]
        i +=1
        length += 1
        imm = b0 | (b1 << 8)
    elif (imm_size == 4):
        imm_size_mux = 0b10 #4 bytes
        b0 = instr[i]
        i += 1
        length += 1
        b1 = instr[i]
        i += 1
        length += 1
        b2 = instr[i]
        i += 1
        length += 1
        b3 = instr[i]
        i += 1
        length += 1
        imm = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24) #little endian
    

    #New EIP
    #print("i value: ", i)
    eip_new = i #add length of instruction + 1 to pc to jump to start of next instruction
    instr_cnt[0] += 1

    #Print to dumpfile 
    if dump_file is not None:
        with open(dump_file, "a") as f:  # append mode
            f.write("=== Predecode Output ===\n")
            f.write(f"Instruction count: {instr_cnt[0]}\n")
            f.write(f"prefix_mux       : {prefix_mux}\n")
            f.write(f"ext_opcode       : {ext_opcode}\n")
            f.write(f"opcode           : {hex(opcode)}\n")
            f.write(f"modrm            : {hex(modrm)}\n")
            f.write(f"sib              : {hex(sib)}\n")
            f.write(f"disp             : {hex(disp)}\n")
            f.write(f"disp_size_mux    : {disp_size_mux}\n")
            f.write(f"imm              : {hex(imm)}\n")
            f.write(f"imm_size_mux     : {imm_size_mux}\n")
            f.write(f"eip              : {hex(eip)}\n")
            f.write(f"eip_new          : {hex(eip_new)}\n")
            f.write(f"reg0_mux         : {reg0_mux[0]}\n")
            f.write(f"imm_type         : {imm_type[0]:02b}\n")
            f.write("========================\n")

    instr_obj = DecodedInstruction(
        eip=eip,
        eip_new=eip_new,
        prefix_mux=prefix_mux,
        ext_opcode=ext_opcode,
        opcode=opcode,
        modrm=modrm,
        sib=sib,
        disp=disp,
        disp_size_mux=disp_size_mux,
        imm=imm,
        imm_size_mux=imm_size_mux,
        reg0_mux=reg0_mux[0],
        imm_type=imm_type[0],
        instr_len=length
    )

    return instr_obj


def decode(mem, eip):    
    #Dumpfile
    dump_file = "decode_dump.txt"
    open(dump_file, "w").close() # Clear previous dump

    instrs = []
    instr_cnt = [0]
    decoded = None
    while True:
        #Choose correct eip value
        if eip not in mem:
            greater_keys = [addr for addr in mem.keys() if addr > eip]
            if not greater_keys:
                #print(f"No more instructions after {hex(eip)}")
                break
            
            eip = min(greater_keys)
            #print(f"Jumping to next instruction at {hex(eip)}")
        #else: 
            #print("eip in mem")
        
        #decode all instructions
        sorted_addrs = sorted(mem.keys())
        instr_str = bytes(int(mem[addr], 16) for addr in sorted_addrs)
        formatted_instr_str = " ".join(f"{b:02x}" for b in instr_str)
        decoded = predecode(formatted_instr_str, eip, instr_cnt, dump_file=dump_file)
        instrs.append(decoded)
        eip = decoded.eip_new

    return instrs





