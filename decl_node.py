
from clang.cindex import Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File, TypeKind, AccessSpecifier
from clang.cindex import Cursor, CursorKind
from node_type import cursor_to_type, type_to_type
from decl_string import get_decl, get_result, get_type

def sem_parent_list( cursor ):
    result = []
    if not isinstance( cursor, Cursor ):
        return result
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        return []
    if isinstance( cursor.semantic_parent, Cursor ):
        result = sem_parent_list( cursor.semantic_parent )

    name = cursor.spelling
    result.append( name )
    return result

def access_name( access ):
    result = None
    if access != AccessSpecifier.INVALID:
        result = str( access.name ).lower()
    return result

def decl_location( cursor ):
    loc = ( cursor.location.file.name, cursor.location.line, cursor.location.column )
    return [ loc ]

def decl_node( key, name, cursor ):
    node = {
        'name': name,
        'key': key,
        'kind': cursor_to_type( cursor ),
        'link': '',
        'location': [ cursor.location ],
        'type': type_node( cursor.type ),
        'result': type_node( cursor.result_type ),
        'access': access_name( cursor.access_specifier ),
        'decl': get_decl( cursor ),
        'display': str( cursor.displayname ),
        'comments': [],
        'children': [],
    }
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        node['name'] = ''
        node['decl'] = ''
        node['display'] = 'global'
    elif cursor.kind == CursorKind.CXX_ACCESS_SPEC_DECL:
        node['decl'] = ''
    if node['type'] == None:
        del node['type']
    if node['access'] == None:
        del node['access']
    if node['result'] == None:
        del node['result']
    return node

pointer_kind = [
    TypeKind.POINTER,
    TypeKind.LVALUEREFERENCE,
    TypeKind.MEMBERPOINTER,
]

def type_node( typ ):
    node = None
    if typ and typ.kind != TypeKind.INVALID:
        if typ.kind == TypeKind.FUNCTIONPROTO:
            node = {
                'kind': type_to_type( typ ),
                'name': typ.spelling,
                'result': type_node( typ.get_result() ),
                'variadic': typ.is_function_variadic(),
                'arguments': [type_node(t) for t in typ.argument_types()],
            }
        elif typ.kind == TypeKind.MEMBERPOINTER:
            node = {
                'kind': type_to_type( typ ),
                'name': typ.spelling,
                'class': type_node( typ.get_class_type() ),
                'pointee': type_node( typ.get_pointee() ),
            }
        elif typ.kind == TypeKind.VOID:
            node = {
                'kind': type_to_type( typ ),
                'name': typ.spelling,
            }
        elif typ.kind in pointer_kind:
            node = {
                'kind': type_to_type( typ ),
                'name': typ.spelling,
                'pointee': type_node( typ.get_pointee() ),
            }
        else:
            node = {
                'kind': type_to_type( typ ),
                'name': typ.spelling,
            }
    return node
