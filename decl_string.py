
from pprint import pprint
from clang.cindex import Index, Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File, Type
import re

punct = {
    '&': ' &',
    '&&': ' &&',
    '*': ' *',
    ',': ',\n  ',
    '(': '(\n  ',
    ')': ' )',
    '<': '<\n  ',
    '>': ' >\n',
    '=': ' = ',
    '...': ' ...',
}

simplify = [
    ( re.compile( r'[(]\n  [)]' ), r'( void )' ),
    ( re.compile( r'[(]\n  ([^\n]*) [)]' ), r'( \1 )' ),
    ( re.compile( r':: [*]' ), r'::*' ),
    ( re.compile( r'[)]([a-z])' ), r') \1' ),
]

def get_decl( cursor ):
    result = ''
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        return cursor.spelling
    for tok in cursor.get_tokens():
        if tok.spelling == '{':
            break;
        if tok.kind == TokenKind.COMMENT:
            continue
        if tok.kind == TokenKind.PUNCTUATION:
            result = result.rstrip() + punct.get( tok.spelling, tok.spelling )
        else:
            result = result + tok.spelling + ' '
    result = result.strip()
    for ( regex, replace ) in simplify:
        ( result, _ ) = re.subn( regex, replace, result )
    return result

def get_result( cursor ):
    if cursor.result_type:
        return cursor.result_type.spelling
    return None

def get_type( cursor ):
    if cursor.type:
        return cursor.type.spelling
    return None
