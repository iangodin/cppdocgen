
from clang.cindex import Cursor, CursorKind, TypeKind, TokenKind

mapping_cursor = {
    TokenKind.COMMENT: 'group',
    CursorKind.CXX_METHOD: 'method',
    CursorKind.CLASS_DECL: 'class',
    CursorKind.CLASS_TEMPLATE: 'class',
    CursorKind.STRUCT_DECL: 'struct',
    CursorKind.CXX_ACCESS_SPEC_DECL: 'group',
    CursorKind.CONSTRUCTOR: 'constructor',
    CursorKind.DESTRUCTOR: 'destructor',
    CursorKind.FIELD_DECL: 'field',
    CursorKind.VAR_DECL: 'variable',
    CursorKind.PARM_DECL: 'param',
    CursorKind.TEMPLATE_TYPE_PARAMETER: 'tparam',
    CursorKind.FUNCTION_TEMPLATE: 'function',
    CursorKind.FUNCTION_DECL: 'function',
    CursorKind.NAMESPACE: 'namespace',
    CursorKind.TRANSLATION_UNIT: 'global',
}

def cursor_to_type( cursor ):
    ty = mapping_cursor.get( cursor.kind, None )
    if isinstance( ty, str ):
        return ty
    elif ty == None:
        return 'unknown'
    else:
        return ty( cursor )

mapping_type = {
    TypeKind.AUTO: 'auto',
    TypeKind.ENUM: 'enum',
    TypeKind.BOOL: 'pod',
    TypeKind.CHAR16: 'pod',
    TypeKind.CHAR32: 'pod',
    TypeKind.CHAR_S: 'pod',
    TypeKind.CHAR_U: 'pod',
    TypeKind.INT: 'pod',
    TypeKind.FLOAT: 'pod',
    TypeKind.DOUBLE: 'pod',
    TypeKind.NULLPTR: 'nullptr',
    TypeKind.POINTER: 'pointer',
    TypeKind.LVALUEREFERENCE: 'reference',
    TypeKind.FUNCTIONPROTO: 'function',
    TypeKind.MEMBERPOINTER: 'memberptr',
    TypeKind.RECORD: 'class',
    TypeKind.VOID: 'void',
    TypeKind.UNEXPOSED: 'hidden',
}

def type_to_type( typ ):
    t = mapping_type.get( typ.kind, None )
    if isinstance( t, str ):
        return t
    else:
        return str( typ.kind.name )
