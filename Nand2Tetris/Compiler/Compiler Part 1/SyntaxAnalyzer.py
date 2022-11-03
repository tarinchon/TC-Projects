import re
import sys
import os

def remove_comments_and_whitespace(contents: str) -> list:
    """
    Remove comments and whitespace from the given .jack file.

    :param contents: Jack source code
    :return last_list: Parsed Jack code without comments and whitespace
    """
    # /** */ style API comments
    API_comment = r"(/\*\*.*?\*/\s?)"
    # Replace API comments in source code with empty strings
    without_API_comments = re.sub(API_comment, '', contents, flags=re.DOTALL)
    # /* */ style block comments
    block_comment = r"(/\*.*?\*/\s?)"
    # Replace block comments in source code with empty strings
    without_block_comments = re.sub(block_comment, '', without_API_comments, flags=re.DOTALL)
    # Split resulting text using newline character
    lines = without_block_comments.split('\n')
    # Initialize an empty list to be filled with raw code excluding line comments
    line_list = []
    line_comment = '//'
    # Remove line comments by iterating through "lines" and appending contents 
    # of each line of Jack code without the line comment. If the line only contains
    # a line comment, remove the line comment by itself and don't append anything
    for line in lines:
        if line_comment in line:
            line_comment_start = line.find(line_comment)
            if line[:line_comment_start] != '':
                line_list.append(line[:line_comment_start])
        else:
            # Append lines without line comments only if the lines themselves aren't
            # empty strings or tab characters
            if line != '' and line != '\t':
                line_list.append(line)

    # Split each line of Jack code by whitespace only if the line does not include a 
    # string constant. If the line does include a string constant, append the entire
    # string constant to the list without splitting the string constant by whitespace
    experiment = []
    for line in line_list:
        if '\"' not in line: # line of Jack code does not include a string constant
            experiment.extend(line.split())
        else: # line of Jack code does include a string constant
            # List of indices for quotation marks found in this line of Jack code
            indices = [q.start() for q in re.finditer('\"',line)]
            # Extract the string constant by slicing the line of Jack code by indices 
            # where the quotation marks were found
            string_constant = line[indices[0]:indices[1]+1]
            # Add tokens in lines that do include a string constant in the right order
            # by first extending the list by tokens before the string constant, then 
            # appending the string constant, and finally, extending the list by tokens
            # after the string constant
            experiment.extend(line[:indices[0]].split())
            experiment.append(string_constant)
            experiment.extend(line[indices[1]+1:])
    # Final parsing steps that need to be completed
    last_list = []
    for item in experiment:
        # Split each token by any symbols that are still attached to the token but keep
        # the separators/symbols when splitting
        new_item = re.split('([-~{\.(),;\[\]])',item)
        # Minor fix: need to delete empty strings that surround individual symbols
        new_item = list(filter(None, new_item))
        # Extend last_list by tokens after successfully detaching symbols
        last_list.extend(new_item)
    # Return final parsed list
    return last_list

def tokenizer(parsed_list: list) -> str:
    """
    Tokenize code in given .jack file.

    :param parsed_list: Jack source code in the form of a parsed list where all tokens are separated out
    :return big_string: Tokenizer output as one big string to write out to xml file
    """
    # Initialize list of keywords
    keyword_list = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var',
    'int', 'char', 'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 
    'else', 'while', 'return']
    # Initialize list of symbols
    symbol_list = ['{','}','(',')','[',']','.',',',';','+','-','*','/','|','=','~']
    # Initialize separate list for a subset of the symbols that require special labels
    symbol_subset = ['<','>','\"','&']
    # Initialize tokenizer output string
    big_string = '<tokens>\n'
    token_list = []
    # Iterate through input list, parsed_list, and depending on type of token, output 
    # relevant tags along with the token
    for token in parsed_list:
        if token in keyword_list:
            big_string += '\t<keyword> ' + token + ' </keyword>\n'
            token_list.append(('keyword', token))
        elif token in symbol_list:
            big_string += '\t<symbol> ' + token + ' </symbol>\n'
            token_list.append(('symbol', token))
        elif token in symbol_subset:
            if token == '<':
                big_string += '\t<symbol> &lt; </symbol>\n'
                token_list.append(('symbol', '&lt;'))
            elif token == '>':
                big_string += '\t<symbol> &gt; </symbol>\n'
                token_list.append(('symbol', '&gt;'))
            elif token == '\"':
                big_string += '\t<symbol> &quot; </symbol>\n'
                token_list.append(('symbol', '&quot;'))
            else:
                big_string += '\t<symbol> &amp; </symbol>\n'
                token_list.append(('symbol', '&amp;'))
        elif token.isdigit() and int(token) in range(32768):
            big_string += '\t<integerConstant> ' + token + ' </integerConstant>\n'
            token_list.append(('integerConstant', token))
        elif token.startswith('\"') and token.endswith('\"'):
            token = token.replace('\"','')
            big_string += '\t<stringConstant> ' + token.strip() + ' </stringConstant>\n'
            token_list.append(('stringConstant', token.strip()))
        else:
            big_string += '\t<identifier> ' + token + ' </identifier>\n'
            token_list.append(('identifier', token))
    # Add last tag to tokenizer output string
    big_string += '</tokens>'
    # Return tokenizer output string
    return big_string, token_list

def get_next_token():
    global token_list
    global ptr
    ptr += 1
    if ptr < len(token_list):
        return token_list[ptr]
    else:
        return -1

def peek_next_token():
    global token_list
    global ptr
    if ptr+1 < len(token_list):
        return token_list[ptr+1]
    #else:
    #    return -1

def reset_pointer():
    global ptr
    ptr = -1

def append_this_token():
    global xml_list
    global current_token
    current_token = get_next_token()
    xml_list.append('<'+current_token[0]+'>'+current_token[1]+'</'+current_token[0]+'>\n')

def process_tokens():
    global xml_list
    global current_token
    reset_pointer()
    current_token = get_next_token()
    # Always start compiling with class token
    if current_token[1] == 'class':
        compile_class()
    else:
        return -1

def compile_class():
    global xml_list
    global current_token
    xml_list.append('<class>\n')
    xml_list.append('<'+current_token[0]+'>'+current_token[1]+'</'+current_token[0]+'>\n')
    compile_className()
    # '{'
    append_this_token()
    # classVarDec*
    while peek_next_token()[1] == 'static' or peek_next_token()[1] == 'field':
        compile_classVarDec()
    # subroutineDec*
    while peek_next_token()[1] != '}':
        compile_subroutineDec()
    # '}'
    append_this_token()
    xml_list.append('</class>\n')


def compile_classVarDec():   
    global xml_list
    xml_list.append('<classVarDec>\n')
    # 'static'|'field'
    append_this_token()
    compile_type()
    # varName
    compile_varName()
    # (',',varName)*
    while peek_next_token()[1] == ',':
        # ','
        append_this_token()
        compile_varName()
    # ';'
    append_this_token()
    xml_list.append('</classVarDec>\n')

def compile_type():
    # just need to call append_this_token since all types are tokens 
    # including className, which is an identifier
    append_this_token()

def compile_subroutineDec(): 
    global xml_list
    xml_list.append('<subroutineDec>\n')
    # 'constructor'|'function'|'method'
    append_this_token()
    # 'void'|type
    if peek_next_token()[1] == 'void': 
        append_this_token()
    else:
        compile_type()
    compile_subroutineName()
    # '('
    append_this_token()
    compile_parameterList()
    # ')'
    append_this_token()
    compile_subroutineBody()
    xml_list.append('</subroutineDec>\n')

def compile_parameterList():
    global xml_list
    xml_list.append('<parameterList>\n')
    while peek_next_token()[1] != ')':
        compile_type()
        compile_varName()
        while peek_next_token()[1] == ',':
            # ','
            append_this_token()
            compile_type()
            compile_varName()
    xml_list.append('</parameterList>\n')


def compile_subroutineBody():
    global xml_list
    xml_list.append('<subroutineBody>\n')
    # '{'
    append_this_token()
    while peek_next_token()[1] not in ['let', 'if', 'while', 'do', 'return']:
        compile_varDec()
    compile_statements()
    # '}'
    append_this_token()
    xml_list.append('</subroutineBody>\n')

def compile_varDec():
    global xml_list
    xml_list.append('<varDec>\n')
    # 'var'
    append_this_token()
    compile_type()
    compile_varName()
    while peek_next_token()[1] != ';':
        # ','
        append_this_token()
        compile_varName()
    # ';'
    append_this_token()
    xml_list.append('</varDec>\n')

def compile_className(): 
    append_this_token()

def compile_subroutineName():
    append_this_token()

def compile_varName():
    append_this_token()

def compile_statements():
    xml_list.append('<statements>\n')
    while peek_next_token()[1] in ['let', 'if', 'while', 'do', 'return']:
        compile_statement()
    xml_list.append('</statements>\n')

def compile_statement():
    if peek_next_token()[1] == 'let':
        compile_letStatement()
    elif peek_next_token()[1] == 'if':
        compile_ifStatement()
    elif peek_next_token()[1] == 'while':
        compile_whileStatement()
    elif peek_next_token()[1] == 'do':
        compile_doStatement()
    else:
        compile_returnStatement()

def compile_letStatement(): 
    global xml_list
    xml_list.append('<letStatement>\n')
    # 'let'
    append_this_token()
    # varName
    compile_varName()
    if peek_next_token()[1] == '[':
        # '['
        append_this_token()
        compile_expression()
        # ']'
        append_this_token()
    # '='
    append_this_token()
    compile_expression()
    # ';'
    append_this_token()
    xml_list.append('</letStatement>\n')

def compile_ifStatement():
    global xml_list
    xml_list.append('<ifStatement>\n')
    # 'if'
    append_this_token()
    # '('
    append_this_token()
    compile_expression()
    # ')'
    append_this_token()
    # '{'
    append_this_token()
    compile_statements()
    # '}'
    append_this_token()
    if peek_next_token()[1] == 'else':
        # 'else'
        append_this_token()
        # '{'
        append_this_token()
        compile_statements()
        # '}'
        append_this_token()
    xml_list.append('</ifStatement>\n')

def compile_whileStatement():
    global xml_list
    xml_list.append('<whileStatement>\n')
    # 'while'
    append_this_token()
    # '('
    append_this_token()
    compile_expression()
    # ')'
    append_this_token()
    # '{'
    append_this_token()
    compile_statements()
    # '}'
    append_this_token()
    xml_list.append('</whileStatement>\n')

def compile_doStatement():
    global xml_list
    xml_list.append('<doStatement>\n')
    # 'do'
    append_this_token()
    compile_subroutineCall()
    # ';'
    append_this_token()
    xml_list.append('</doStatement>\n')

def compile_returnStatement():
    global xml_list
    xml_list.append('<returnStatement>\n')
    # 'return'
    append_this_token()
    if peek_next_token()[1] != ';':
        compile_expression()
    # ';'
    append_this_token()
    xml_list.append('</returnStatement>\n')

def compile_expression():
    global xml_list
    xml_list.append('<expression>\n') 
    compile_term()
    while peek_next_token()[1] in ['+','-','*','/','&amp;','|','&lt;','&gt;','=']:
        compile_op()
        compile_term()
    xml_list.append('</expression>\n')

def compile_term():
    global xml_list
    xml_list.append('<term>\n')    
    if peek_next_token()[0] in ['integerConstant', 'stringConstant']:
        append_this_token()
    elif peek_next_token()[0] == 'identifier': #varName or subroutineCall
        append_this_token()
        if peek_next_token()[1] == '[':
            # '['
            append_this_token()
            compile_expression()
            # ']'
            append_this_token()
        if peek_next_token()[1] in ['.','(']:
            compile_subroutineCall()
    elif peek_next_token()[1] in ['true','false','null','this']:
        compile_keywordConstant()
    elif peek_next_token()[1] == '(':
        # '('
        append_this_token()
        compile_expression()
        # ')'
        append_this_token()
    elif peek_next_token()[1] in ['-','~']:
        compile_unaryOp()
        compile_term()
    xml_list.append('</term>\n')
    


def compile_subroutineCall():
    if peek_next_token()[1] not in ['.', '(']:
        append_this_token()
    if peek_next_token()[1] != '.':
        # '('
        append_this_token()
        compile_expressionList()
        # ')'
        append_this_token()
    else:
        # '.'
        append_this_token()
        compile_subroutineName()
        # '('
        append_this_token()
        compile_expressionList()
        # ')'
        append_this_token()     


def compile_expressionList():
    global xml_list
    xml_list.append('<expressionList>\n')
    if peek_next_token()[1] != ')':
        compile_expression()
        while peek_next_token()[1] == ',':
            # ','
            append_this_token()
            compile_expression()
    xml_list.append('</expressionList>\n')

def compile_op():
    append_this_token()

def compile_unaryOp():
    # '-'|'~'
    append_this_token() 

def compile_keywordConstant():
    append_this_token()  

def main():
    global xml_list
    global token_list
    xml_list = []
    if sys.argv[1].endswith('.jack'):     # Handle a single file
        with open(sys.argv[1], 'r') as infile:
            # read in contents of .jack file as one big string
            contents = infile.read()
            # pass in contents to remove_comments_and_whitespace function to remove comments and whitespace
            Jack_code = remove_comments_and_whitespace(contents)
            # tokenizer function returns both a string containing all tokens found in Jack code and a list
            # of tokens containing all tokens found in Jack code
            big_string, token_list = tokenizer(Jack_code)
        process_tokens()
        file_name = sys.argv[1].split('.')[0] + 'Copy.xml'
        with open(file_name, 'w') as outfile:
            for line_of_xml in xml_list:
                outfile.write(line_of_xml)
    else:    # Handle a file directory
        Jack_code_directory = sys.argv[1]
        for file in os.listdir(Jack_code_directory):
            if file.endswith('.jack'):
                start = len(xml_list)
                file_path = Jack_code_directory + '/' + file
                with open(file_path, 'r') as infile:
                    contents = infile.read()
                    Jack_code = remove_comments_and_whitespace(contents)
                    big_string, token_list = tokenizer(Jack_code)
                process_tokens()
                list_to_write = xml_list[start:]
                file_name = file_path.split('/')[-1].split('.')[0] + 'Copy.xml'
                with open(file_name, 'w') as outfile:
                    for line_of_xml in list_to_write:
                        outfile.write(line_of_xml)


if __name__ == '__main__':
    main()