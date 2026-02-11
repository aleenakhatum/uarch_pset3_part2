#Libraries
import sys

#Files
from utils import *
from registers import *
from decoder import *
from execute import *
from memory import *

#Main
def main():
    if len(sys.argv) < 2:
        print("No input memory file passed.")
        print("Try Run Command: <python3 isl.py mem.txt>")
        return

    print("Run Successful")
    with open("results.txt", "w") as f:
        f.write("START OF SIMULATION TRACE\n")
        f.write("="*60 + "\n\n")

    mem_file = sys.argv[1]

    mem = {}
    load_mem_file(mem, mem_file) #parse inpute file
    
    eip = 0
    instrs_decoded = decode(mem, eip)

    state = Registers()
    for instr in instrs_decoded:
        execute(instr, state, mem)
        write_results(state, mem, "results.txt")

    #     dump_state_to_results()

    #     if instr.mnemonic == "HLT"
    #         break

if __name__ == "__main__":
    main()
