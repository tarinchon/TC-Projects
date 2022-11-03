import sys
import re

def remove_comments_and_whitespace(contents: str) -> str:
    """
    Remove comments and whitespace from the given .in file.

    :param contents: Source code
    :return: Source code without comments and whitespace
    """
    # // style line comments
    line_comment = r"(//.*$)"
    without_line_comments = re.sub(line_comment, "", contents, flags=re.MULTILINE)

    # /* */ style block comments
    block_comment = r"(/\*.*?\*/\s?)"
    without_line_and_block_comments = re.sub(block_comment, "", without_line_comments, flags=re.DOTALL)
    lines = without_line_and_block_comments.split()

    lines = list(filter(None, lines))

    lines = '\n'.join(line for line in lines) 

    return lines 

def extend_symbol_table(assembly_language):
    """
    Extend symbol table with labels and variables found in inputted assembly language.

    :param assembly_langugage: Assembly code without comments and whitespace
    :return extended_symbol_table: Extended symbol table that includes labels and variables found in assembly code and their respective ROM and RAM locations
    :return copy_list: Assembly code without comments, whitespace, and labels in a list format
    """
    # Create predefined symbol table
    symbol_table = {'SP':0, 'LCL':1, 'ARG':2, 'THIS':3, 'THAT':4, 'R0':0, 'R1':1, 'R2':2, 'R3':3, 'R4':4, 'R5':5, 'R6':6, 'R7':7, 'R8':8,
    'R9':9, 'R10':10, 'R11':11, 'R12':12, 'R13':13, 'R14':14, 'R15':15, 'SCREEN': 16384, 'KBD':24576}

    # Split the comment- and whitespace-free assembly language into separate lines of code
    new_list = assembly_language.split('\n')
    # Initialize empty list and line number counter for operations in lines 72 to 77
    copy_list = []
    line_number=0
    
    # Add labels to symbol table and create a copy of new_list that excludes labels
    for item in new_list:
        if item[0] != '(':
            copy_list.append(item)
            line_number += 1
        else:
            symbol_table[item[1:-1]] = line_number

    # Add variables to symbol table starting at RAM location 16
    count2 = 16
    for item in new_list:
        if item.startswith('@') and item[1:] not in symbol_table:
            try:
                testing = int(item[1:])
            except:
                symbol_table[item[1:]] = count2
                count2 += 1
            else:
                if not item[1:].isdigit():
                    symbol_table[item[1:]] = count2
                    count2 += 1 

    return symbol_table, copy_list

def translate(extended_symbol_table, copy_list) -> str:
    """
    Translate inputted assembly language into machine code.

    :param extended_symbol_table: Extended symbol table that includes labels and variables and their respective ROM and RAM locations
    :param copy_list: Assembly code without comments, whitespace, and labels in a list format
    :return machine_code: Machine language instructions as one big string
    """
    machine_code_list = []
    for item in copy_list:
        if item.startswith('@') and item[1:].isdigit(): #decode A-instruction
            machine_code_line = bin(int(item[1:])).replace('0b', '')
            machine_code_line = machine_code_line.zfill(16)
            machine_code_list.append(machine_code_line)
        elif item.startswith('@') and not item[1:].isdigit(): #decode A-instruction
            machine_code_line = bin(extended_symbol_table[item[1:]]).replace('0b', '')
            machine_code_line = machine_code_line.zfill(16)
            machine_code_list.append(machine_code_line)
        else: #decode C-instruction
            machine_code_line = decode_C_instr(item)
            if machine_code_line is not None:
                machine_code_list.append(machine_code_line)
    machine_code = '\n'.join(machine_code_list)
    return machine_code

def decode_C_instr(item):
    """
    Decode inputted C-instruction into machine language.

    :param item: a single C-instruction in assembly language
    :return c_instr: a single C-instruction in machine language
    """
    # Create mnemonic table for dest bits
    dest_dict = {'':'000','M':'001','D':'010','MD':'011','A':'100','AM':'101','AD':'110','AMD':'111'}
    # Create computation table for a=0
    comp_dict_1 = {'0':'101010','1':'111111','-1':'111010','D':'001100','A':'110000', '!D':'001101',
    '!A':'110001','-D':'001111','-A':'110011','D+1':'011111','A+1':'110111','D-1':'001110','A-1':'110010',
    'D+A':'000010','D-A':'010011','A-D':'000111','D&A':'000000', 'D|A':'010101'}
    # Create computation table for a=1
    comp_dict_2 = {'M':'110000', '!M':'110001', '-M':'110011', 'M+1':'110111', 'M-1':'110010',
    'D+M':'000010', 'D-M':'010011','M-D':'000111','D&M':'000000','D|M':'010101'}
    # Create mnemonic table for jump bits
    jump_dict = {'':'000','JGT':'001','JEQ':'010','JGE':'011','JLT':'100','JNE':'101','JLE':'110','JMP':'111'}
    c_instr = '111'
    if '=' in item and ';' in item:
        equalsign_index = item.index('=')
        semicolon_index = item.index(';')
        dest = item[:equalsign_index]
        comp = item[equalsign_index+1:semicolon_index]
        jump = item[semicolon_index+1:]
    elif '=' in item and ';' not in item:
        equalsign_index = item.index('=')
        dest = item[:equalsign_index]
        comp = item[equalsign_index+1:]
        jump=''
    elif ';' in item and '=' not in item:
        semicolon_index = item.index(';')
        dest=''
        comp = item[:semicolon_index]
        jump = item[semicolon_index+1:]
    else:
        dest=''
        comp = item
        jump=''
    
    # Determine whether a=0 or a=1
    if 'M' in comp or 'D' and 'M' in comp: 
        c_instr = c_instr + '1'
    else:
        c_instr = c_instr + '0'
    
    #Depending on the value of a, look up computation bits in correct computation table and concatenate with destination and jump bits
    if c_instr[3] == '0' and comp != '':
        c_instr = c_instr + comp_dict_1[comp]
        c_instr = c_instr + dest_dict[dest] + jump_dict[jump]
    else:
        c_instr = c_instr + comp_dict_2[comp]
        c_instr = c_instr + dest_dict[dest] + jump_dict[jump]
    return c_instr

def main():
    with open(sys.argv[1], 'r') as infile:
        contents = infile.read()
        assembly_language = remove_comments_and_whitespace(contents)
        extended_symbol_table, copy_list = extend_symbol_table(assembly_language)
        machine_language = translate(extended_symbol_table, copy_list)  
    file_name = sys.argv[1]
    file_name = file_name.replace('.asm', '.hack')
    f = open(file_name, 'w')
    f.write(machine_language)
    f.close()

if __name__ == '__main__':
    main()