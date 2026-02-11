from enum import Enum

class DecodedInstruction:
    def __init__(
        self,
        eip,
        eip_new,
        prefix_mux,
        ext_opcode,
        opcode,
        modrm,
        sib,
        disp,
        disp_size_mux,
        imm,
        imm_size_mux,
        reg0_mux,
        imm_type,
        instr_len
    ):
        self.eip = eip
        self.eip_new = eip_new
        self.prefix_mux = prefix_mux
        self.ext_opcode = ext_opcode
        self.opcode = opcode
        self.modrm = modrm
        self.sib = sib
        self.disp = disp
        self.disp_size_mux = disp_size_mux
        self.imm = imm
        self.imm_size_mux = imm_size_mux
        self.reg0_mux = reg0_mux
        self.imm_type = imm_type
        self.instr_len = instr_len

    def __repr__(self):
        return (
            f"DecodedInstruction("
            f"eip={hex(self.eip)}, "
            f"eip_new={hex(self.eip_new)}, "
            f"len={self.instr_len}, "
            f"opcode={hex(self.opcode)}, "
            f"modrm={hex(self.modrm)}, "
            f"sib={hex(self.sib)}, "
            f"disp={hex(self.disp)}, "
            f"imm={hex(self.imm)})"
        )
