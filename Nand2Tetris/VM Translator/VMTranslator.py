import sys
import re
import os

def remove_comments_and_whitespace(contents: str) -> list:
    """
    Remove comments and whitespace from the given .vm file.

    :param contents: VM source code
    :return list_of_lists: VM source code without comments and whitespace
    """
    # /* */ style block comments
    block_comment = r"(/\*.*?\*/\s?)"
    # Replace block comments in source code with empty strings
    without_block_comments = re.sub(block_comment, '', contents, flags=re.DOTALL)
    # Split resulting text using newline character
    lines = without_block_comments.split('\n')
    # Initialize an empty list to be filled with parsed VM commands
    line_list = []
    line_comment = '//'
    # Remove line comments by iterating through "lines" and appending contents 
    # of each line of VM code without the line comment. If the line only contains
    # a line comment, remove the line comment by itself and don't append anything
    for line in lines:
        if line_comment in line:
            line_comment_start = line.find(line_comment)
            if line[:line_comment_start] != '':
                line_list.append(line[:line_comment_start])
        else:
            if line != '':
                line_list.append(line)
    # Split each VM command in line_list based on whitespace in order to unpack
    # each VM command into its various components 
    list_of_lists = []
    for line in line_list:
        list_of_lists.append(line.split())

    return list_of_lists

def generate_bootstrap_code():
    """
    Generate bootstrap code to attach to the beginning of output file

    :return: assembly language version of bootstrap code
    """
    # Include comment indicating that chunk of assembly language is bootstrap code
    Hack_assembly = '// bootstrap code\n'
    # Initialize assembly language string to include bootstrap code
    Hack_assembly += '@256\nD=A\n@SP\nM=D\n'
    # Initialize VM command, call Sys.init 0, as a list
    command = ['call', 'Sys.init', '0']
    # Translate VM command, call Sys.init 0
    Hack_assembly = translate_call(command,Hack_assembly,counter2=None,functions_list=['Bootstrap$ret'])
    return Hack_assembly

def generate_comment(line, Hack_assembly):
    """
    Generate comment that indicates which VM command we're translating below the comment

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Hack assembly code the includes comment
    """
    Hack_assembly += '// ' + ' '.join(line) + '\n'
    return Hack_assembly

def translate_to_assembly(VM_code):
    """
    Translate VM code to assembly language by iterating through each line of VM code and calling relevant function.

    :param VM_code: list of lists where each constitutent list is a single VM command unpacked into its various components
    :return Hack_assembly: Hack assembly language translated from VM code that was inputted into function
    """
    # Initialize assembly code as empty string
    Hack_assembly = ''
    # Create and initialize counters that will differentiate labels in assembly language
    counter = 1
    counter2 = 1    
    # Create a list of functions whose length is the number of functions created and last function is
    # the most recently created function
    functions_list = []
    # Helper data for translating push and pop commands
    symbols = {'argument': 'ARG', 'local': 'LCL', 'this': 'THIS', 'that': 'THAT'}
    # Helper data for translating return command 
    return_helper_data = {'2': 'THIS', '3': 'ARG', '4': 'LCL'}
    # Translate each line of VM code into assembly language
    for line in VM_code:
        Hack_assembly = generate_comment(line, Hack_assembly)
        if line[0] in ['add','sub','and','or','not','neg','gt','lt','eq']:
            Hack_assembly, counter = translate_arithmetic(line, Hack_assembly, counter)
        elif line[0] == 'push':
            Hack_assembly = translate_push(line, Hack_assembly, symbols, functions_list)
        elif line[0] == 'pop':
            Hack_assembly = translate_pop(line, Hack_assembly, symbols, functions_list)
        elif line[0] == 'label':    
            Hack_assembly = translate_label(line,Hack_assembly,functions_list)
        elif line[0] == 'goto':    
            Hack_assembly = translate_goto(line,Hack_assembly,functions_list)
        elif line[0] == 'if-goto':    
            Hack_assembly = translate_ifgoto(line,Hack_assembly, functions_list)
        elif line[0] == 'function':
            function_name = line[1]
            functions_list.append(function_name)
            num_vars = int(line[2])
            Hack_assembly = translate_function(line,function_name, num_vars, Hack_assembly)
        elif line[0] == 'return':
            Hack_assembly = translate_return(line,Hack_assembly,return_helper_data)
        elif line[0] == 'call':
            Hack_assembly, counter2 = translate_call(line,Hack_assembly,counter2,functions_list)
    return Hack_assembly

def translate_call(line, Hack_assembly, counter2, functions_list):
    """
    Translate VM call command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param counter2: Counter included in every label name that ensures labels are unique
    :return Hack_assembly: Hack assembly code corresponding to inputted call command
    :return counter2: Incremented counter that will be passed into next function call to translate_call
    """
    # name of current function
    function_name = functions_list[-1]
    # call command helper data
    call_helper_data = {0:'LCL', 1:'ARG', 2:'THIS', 3:'THAT'}
    # push returnAddress
    if counter2 is not None:
        Hack_assembly += '@' + function_name + str(counter2) + '\n'
    else:
        Hack_assembly += '@' + function_name + '\n'
    Hack_assembly += 'D=A\n@SP\nAM=M+1\nA=A-1\nM=D\n'
    # push LCL, ARG, THIS, THAT
    for x in range(4):
        Hack_assembly += '@' + call_helper_data[x] + '\n'
        Hack_assembly += 'D=M\n@SP\nAM=M+1\nA=A-1\nM=D\n'
    # ARG = SP-5-nArgs
    Hack_assembly += '@SP\nD=M\n@' + str(int(line[2])+5) + '\nD=D-A\n@ARG\nM=D\n'
    # LCL = SP
    Hack_assembly += '@SP\nD=M\n@LCL\nM=D\n'
    # goto f
    Hack_assembly += '@' + line[1] + '\n0;JMP\n'
    # (returnAddress)
    if counter2 is not None:
        Hack_assembly += '(' + function_name + str(counter2) + ')\n'
        counter2 += 1
        return Hack_assembly, counter2
    else:
        Hack_assembly += '(' + function_name + ')\n'
        return Hack_assembly

def translate_return(line,Hack_assembly,return_helper_data):
    """
    Translate VM return command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param return_helper_data: Helper data for translating return command
    :return Hack_assembly: Hack assembly code corresponding to inputted return command
    """
    # frame=LCL
    Hack_assembly += '@LCL\nD=M\n@FRAME\nM=D\n'
    # retrAddr = *(frame-5)
    Hack_assembly += '@FRAME\nD=M\n@5\nA=D-A\nD=M\n@RET\nM=D\n'
    # *ARG=pop()
    Hack_assembly += '@SP\nAM=M-1\nD=M\n@ARG\nA=M\nM=D\n'
    # SP=ARG+1
    Hack_assembly += '@ARG\nD=M\n@SP\nM=D+1\n'
    # THAT = *(frame-1)
    Hack_assembly += '@FRAME\nA=M-1\nD=M\n@THAT\nM=D\n'
    # THIS\ARG\LCL = *(frame-2\3\4)
    for x in return_helper_data.keys():
        Hack_assembly += '@FRAME\nD=M\n'
        Hack_assembly += '@' + x + '\n'
        Hack_assembly += 'A=D-A\nD=M\n'
        Hack_assembly += '@' + return_helper_data[x] + '\nM=D\n'
    # goto retAddr
    Hack_assembly += '@RET\nA=M\n0;JMP\n'
    return Hack_assembly

def translate_label(line, Hack_assembly, functions_list):
    """
    Translate VM label command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param functions_list: List of functions defined so far
    :return Hack_assembly: Hack assembly code corresponding to inputted label command
    """
    label_name = line[1]
    if len(functions_list) > 0:
        function_name = functions_list[-1]
        Hack_assembly += '(' + function_name + '$' + label_name + ')\n'
    else:
        Hack_assembly += '(' + label_name + ')\n'
    return Hack_assembly

def translate_ifgoto(line, Hack_assembly, functions_list):
    """
    Translate VM if-goto command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param functions_list: List of functions defined so far
    :return Hack_assembly: Hack assembly code corresponding to inputted if-goto command
    """
    labelName = line[1]
    Hack_assembly += '@SP\nAM=M-1\nD=M\n'
    if len(functions_list) > 0:
        function_name = functions_list[-1]
        Hack_assembly += '@' + function_name + '$' + labelName + '\n'
    else:
        Hack_assembly += '@' + labelName + '\n'
    Hack_assembly += 'D;JNE\n'
    return Hack_assembly

def translate_goto(line, Hack_assembly, functions_list):
    """
    Translate VM goto command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param functions_list: List of functions defined so far
    :return Hack_assembly: Hack assembly code corresponding to inputted goto command
    """
    label_name = line[1]
    if len(functions_list) > 0:
        function_name = functions_list[-1]
        Hack_assembly += '@' + function_name + '$' + label_name + '\n'
    else:
        Hack_assembly += '@' + label_name + '\n'
    Hack_assembly += '0;JMP\n'
    return Hack_assembly

def translate_function(line, function_name, num_vars, Hack_assembly):
    """
    Translate VM function command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param function_name: Name of the function being declared
    :param num_vars: Number of local variables being initialized for the function being declared
    :return Hack_assembly: Hack assembly code corresponding to inputted function command
    """
    Hack_assembly += '('+ function_name +')\n' 
    for x in range(num_vars):
        Hack_assembly += '@0\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
    return Hack_assembly

def translate_arithmetic(line, Hack_assembly, counter):
    """
    Translate VM arithmetic-logical command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param counter: Counter included in every label name that ensures labels are unique
    :return Hack_assembly: Hack assembly code corresponding to inputted arithmetic-logical command
    :return counter: Incremented counter that will be passed into next function call to translate_arithmetic
    """
    if line[0] in ['add','sub']:
        op = '@SP\nAM=M-1\nD=M\nA=A-1\n'
        if line[0] == 'add':
            op += 'M=D+M\n'
        else:
            op += 'M=M-D\n'
        Hack_assembly = Hack_assembly + op
    elif line[0] in ['and','or']:
        op = '@SP\nAM=M-1\nD=M\nA=A-1\n'
        if line[0] == 'and':
            op += 'M=M&D\n'
        else:
            op += 'M=M|D\n'            
        Hack_assembly = Hack_assembly + op          
    elif line[0] in ['not','neg']:
        op = '@SP\nA=M-1\n'
        if line[0] == 'not':
            op += 'M=!M\n'
        else:
            op += 'M=-M\n'
        Hack_assembly = Hack_assembly + op
    elif line[0] in ['gt','lt','eq']:
        op = '@SP\nAM=M-1\nD=M\nA=A-1\nD=M-D\nM=-1\n'
        op += '@CONTINUE' + str(counter) + '\n'
        if line[0] == 'gt':
            op += 'D;JGT\n'
        elif line[0] == 'lt':
            op += 'D;JLT\n'
        else:
            op += 'D;JEQ\n'
        op += '@SP\nA=M-1\nM=0\n'
        op += '(CONTINUE' + str(counter) +')\n'
        counter += 1
        Hack_assembly = Hack_assembly + op
    return Hack_assembly, counter

def translate_push(line, Hack_assembly, symbols, functions_list):
    """
    Translate VM push command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param symbols: Dictionary of pre-defined symbols to be used in translation
    :return: Hack assembly code corresponding to inputted push command
    """
    # Depending on the segment, line[1], and index, line[2], translate push command into assembly code
    if line[1] == 'constant':
        op = '@' + line[2] + '\n'
        op += 'D=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        Hack_assembly = Hack_assembly + op
    elif line[1] in ['argument', 'local', 'this', 'that']:
        op = '@' + symbols[line[1]] + '\n'
        op += 'D=M\n'
        op += '@' + line[2] + '\n'
        op += 'A=A+D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        Hack_assembly = Hack_assembly + op
    elif line[1] == 'pointer':
        if line[2] == '0':
            op = '@THIS\n'
        else:
            op = '@THAT\n'
        op += 'D=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        Hack_assembly = Hack_assembly + op                    
    elif line[1] == 'temp':
        i = 5 + int(line[2])
        op ='@' + str(i) + '\n'
        op += 'D=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        Hack_assembly = Hack_assembly + op
    elif line[1] == 'static':
        op = '@' + functions_list[-1].split('.')[0] + line[2] + '\n'
        op += 'D=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'
        Hack_assembly = Hack_assembly + op
    # Return translation of push command to calling function
    return Hack_assembly

def translate_pop(line, Hack_assembly, symbols, functions_list):
    """
    Translate VM pop command.

    :param line: A single VM command unpacked into its various components, in the form of a list
    :param Hack_assembly: Body of assembly code translated thus far from VM code
    :param symbols: Dictionary of pre-defined symbols to be used in translation
    :return: Hack assembly code corresponding to inputted pop command
    """
    # Depending on the segment, line[1], and index, line[2], translate pop command into assembly code
    if line[1] in ['argument', 'local', 'this', 'that']:
        op = '@' + symbols[line[1]] + '\n'
        op += 'D=M\n'
        op += '@' + line[2] + '\n'
        op += 'D=A+D\n@R13\nM=D\n@SP\nAM=M-1\nD=M\n@R13\nA=M\nM=D\n'
        Hack_assembly = Hack_assembly + op
    elif line[1] == 'pointer':
        op = '@SP\nAM=M-1\nD=M\n'
        if line[2] == '0':
            op +='@THIS\n'
        else:
            op +='@THAT\n'
        op += 'M=D\n'
        Hack_assembly = Hack_assembly + op
    elif line[1] == 'temp':
        i = 5 + int(line[2])
        op = '@SP\nAM=M-1\nD=M\n'
        op +='@' + str(i) + '\n'
        op += 'M=D\n'
        Hack_assembly = Hack_assembly + op                                
    elif line[1] == 'static':
        op = '@SP\nAM=M-1\nD=M\n'
        op += '@' + functions_list[-1].split('.')[0] + line[2] + '\n'
        op += 'M=D\n'
        Hack_assembly = Hack_assembly + op
    # Return translation of pop command to calling function
    return Hack_assembly

def main():
    if sys.argv[1].endswith('.vm'):     # Handle a single file
        with open(sys.argv[1], 'r') as infile:
            contents = infile.read()
            VM_language = remove_comments_and_whitespace(contents)
            assembly_language = translate_to_assembly(VM_language)
        file_name = sys.argv[1]
        file_name = file_name.replace('.vm', '.asm')
        f = open(file_name, 'w')
        f.write(assembly_language)
        f.close()
    else:    # Handle a file directory
        code_list = []
        VM_code_directory = sys.argv[1]
        bootstrap_code = generate_bootstrap_code()
        code_list.extend(bootstrap_code.split('\n'))
        for file in os.listdir(VM_code_directory):
            if file.endswith('.vm'):
                infile = VM_code_directory + '/' + file
                f = open(infile, 'r')
                contents = f.read()
                f.close()
                VM_language = remove_comments_and_whitespace(contents)
                assembly_language = translate_to_assembly(VM_language)
                code_list.extend(assembly_language.split('\n'))
        code_list = list(filter(None, code_list))
        file_name = VM_code_directory.split('/')[-1] + '.asm'
        with open(file_name, 'w') as outfile:
            for code_line in code_list:
                outfile.write(code_line + '\n')


if __name__ == '__main__':
    main()