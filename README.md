# uarch_pset3_part2
Part A:

Define: 
GPR - General Purpose Register
SegR - Segment Register
MEM - Memory
Virtual Address - Effective Address + (SegR << 16)
Effective Address - Base + Displacement (no SIB)

All Addressing Modes: Immediate, Register, Base + Displacement 

If base = EBP or ESP (SS<<16)

1. ADD 

Mnemonic: ADD EAX, imm32
Opcode: 05 id	
    (register) EAX <- EAX + imm32

Mnemonic: ADD r/m32, imm32
Opcode: 81 /0 id
    (indirect) MEM[GPR + SegR<<16] <- MEM[GPR + SegR<<16] + imm32
    (register) GPR <- GPR + imm32
    (base + disp32) MEM[GPR + disp32 + SegR<<16] <- MEM[GPR + disp32 + SegR<<16] + imm32
    (base + disp8) MEM[GPR + SEXT(disp8) + SegR<<16] <- MEM[GPR + SEXT(disp8) + SegR<<16] + imm32
    (absolute) MEM[disp32 + SegR<<16] <- MEM[disp32 + SegR<<16] + imm32

Mnemonic: ADD r/m32,imm8
Opcode: 83 /0 ib	
    (indirect) MEM[GPR + SegR<<16] <- MEM[GPR + SegR<<16] + SEXT(imm8)
    (register) GPR <- GPR + SEXT(imm8)
    (base + disp32) MEM[GPR + disp32 + SegR<<16] <- MEM[GPR + disp32+ SegR<<16] + SEXT(imm8)
    (base + disp8) MEM[GPR + SEXT(disp8) + SegR<<16] <- MEM[GPR + SEXT(disp8) + SegR<<16] + SEXT(imm8)
    (absolute) MEM[disp32 + SegR<<16] <- MEM[disp32 + SegR<<16] + SEXT(imm8)


Mnemonic: ADD r/m32,r32
Opcode: 01 /r	
    (indirect) MEM[GPR_rm + SegR<<16] <- MEM[GPR_rm + SegR<<16] + GPR_reg
    (register) GPR_rm <- GPR_rm + GPR_reg
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- MEM[GPR_rm + disp32+ SegR<<16] + GPR_reg
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- MEM[GPR_rm + SEXT(disp8) + SegR<<16] + GPR_reg
    (absolute) MEM[disp32 + SegR<<16] <- MEM[disp32 + SegR<<16] + GPR_reg

Mnemonic: ADD r32, r/m32
Opcode: 03 /r
    (indirect) GPR_reg <- GPR_reg + MEM[GPR_rm + SegR<<16]
    (register) GPR_reg <- GPR_reg + GPR_rm
    (base + disp32) GPR_reg <- GPR_reg + MEM[GPR_rm + disp32 + SegR<<16]
    (base + disp8) GPR_reg <- GPR_reg + MEM[GPR_rm + SEXT(disp8) + SegR<<16]
    (absolute) GPR_reg <- GPR_reg + MEM[disp32 + SegR<<16]
   

2. MOV

Mnemonic: MOV r/m32, r32
Opcode: 89 /r
    (indirect) MEM[GPR_rm + SegR<<16] <- GPR_reg
    (register) GPR_rm <- GPR_reg
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- GPR_reg
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- GPR_reg
    (absolute) MEM[disp32 + SegR<<16] <- GPR_reg

Mnemonic: MOV r32, r/m32
Opcode: 8B /r
    (indirect) GPR_reg <- MEM[GPR_rm + SegR<<16]
    (register) GPR_reg <- GPR_rm
    (base + disp32) GPR_reg <- MEM[GPR_rm + disp32 + SegR<<16]
    (base + disp8) GPR_reg <- MEM[GPR_rm + SEXT(disp8) + SegR<<16]
    (absolute) GPR_reg <- MEM[disp32 + SegR<<16]

Mnemonic: MOV r32, imm32
Opcode: B8+ rd
    (register) GPR_reg <- imm32

Mnemonic: MOV r/m32, imm32
Opcode: C7 /0
    (indirect) MEM[GPR_rm + SegR<<16] <- imm32
    (register) GPR_rm <- imm32
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- imm32
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- imm32
    (absolute) MEM[disp32 + SegR<<16] <- imm32


3. SAR 
Mnemonic: SAR r/m32, 1 
Opcode: D1 /7 
    (indirect) MEM[GPR_rm + SegR<<16] <- SEXT(1) MEM[GPR_rm + SegR<<16] 
    (register) GPR_rm <- SEXT(1) GPR_rm 
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- SEXT(1) MEM[GPR_rm + disp32 + SegR<<16] 
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- SEXT(1) MEM[GPR_rm + SEXT(disp8) + SegR<<16] 
    (absolute) MEM[disp32 + SegR<<16] <- SEXT(1) MEM[disp32 + SegR<<16]

Mnemonic: SAR r/m32, CL 
Opcode: D3 /7 
    (indirect) MEM[GPR_rm + SegR<<16] <- SEXT(CL) MEM[GPR_rm + SegR<<16] 
    (register) GPR_rm <- SEXT(CL) GPR_rm 
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- SEXT(CL) MEM[GPR_rm + disp32 + SegR<<16] 
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- SEXT(CL) MEM[GPR_rm + SEXT(disp8) + SegR<<16] 
    (absolute) MEM[disp32 + SegR<<16] <- SEXT(CL) MEM[disp32 + SegR<<16]

Mnemonic: SAR r/m32, imm8 
Opcode: C1 /7 ib 
    (indirect) MEM[GPR_rm + SegR<<16] <- SEXT(imm8) MEM[GPR_rm + SegR<<16] 
    (register) GPR_rm <- SEXT(imm8) GPR_rm 
    (base + disp32) MEM[GPR_rm + disp32 + SegR<<16] <- SEXT(imm8) MEM[GPR_rm + disp32 + SegR<<16] 
    (base + disp8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] <- SEXT(imm8) MEM[GPR_rm + SEXT(disp8) + SegR<<16] 
    (absolute) MEM[disp32 + SegR<<16] <- SEXT(imm8) MEM[disp32 + SegR<<16]

4. JMP (Jump)
Mnemonic: JMP rel32 
Opcode: E9 cd 
    (relative) EIP <- EIP + imm32 (the imm32 is treated as a signed int)

Mnemonic: JMP r/m32 
Opcode: FF /4 
    (indirect) EIP <- MEM[GPR_rm + SegR<<16] 
    (register) EIP <- GPR_rm 
    (base + disp32) EIP <- MEM[GPR_rm + disp32 + SegR<<16] 
    (base + disp8) EIP <- MEM[GPR_rm + SEXT(disp8) + SegR<<16] 
    (absolute) EIP <- MEM[disp32 + SegR<<16]

Mnemonic: JMP ptr16:32 
Opcode: EA cp 
    (far) EIP <- imm32, CS <- imm16



Part B:
Make a copy of all of the files in the directory. The top level file that is used to run main() is isl.py.
To run the simulator, use the following command: 
    <py isl.py mem.txt>
    Note: mem.txt can be any input file (i.e. py isl.py input.txt). 
Ensure that before running, the test case is pasted into mem.txt (or other input file) in the following format:
    0x000: b0 00
    0x002: 04 00
    0x004: 66 b8 34 12
    .
    .
    .

