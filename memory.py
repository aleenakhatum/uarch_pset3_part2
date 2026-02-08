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

# def read8(mem, addr):
#     byte = mem[addr]
#     return {}


#def read16(mem, addr):

#def read32(mem, addr):

#def write8(mem, addr, val):

#def write16(mem, addr, val):

#def write32(mem, addr, val):

                
