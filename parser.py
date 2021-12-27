
from clang.cindex import AccessSpecifier

def compare_location( loc1, loc2 ):
    if loc1.line < loc2.line:
        return True
    if loc1.line == loc2.line:
        return loc1.column < loc2.column
    return False

class Parser:
    def __init__( parser, comments, files ):
        parser.comments = comments
        parser.group = None
        parser.warned = set()
        parser.files = files

    def __call__( parser, node ):
        if str( node.location.file ) not in parser.files:
            return None
        k = node.kind.name
        method = getattr( Parser, node.kind.name, None )
        if method == None:
            method = Parser.unknown
        n = method( parser, node )
        if parser.group != None:
            g = parser.group['group']
            g.append( n )
            if len( g ) == 1:
                n = parser.group
            else:
                n = None
        return n

    def begin_group( parser, name, comments ):
        parser.group = {
            'kind': 'group',
            'name': name[4:].strip(),
            'comments': comments,
            'group': [],
        }

    def gather_comments( parser, loc ):
        result = []
        count = 0
        for c in parser.comments:
            if compare_location( c.location, loc ):
                count = count + 1
                if c.spelling.startswith( '////' ):
                    parser.begin_group( c.spelling, result.copy() )
                    result = []
                else:
                    result.append( c.spelling )
            else:
                break
        parser.comments = parser.comments[count:]
        return result

    def skip_comments( parser, loc ):
        count = 0
        for c in parser.comments:
            if compare_location( c.location, loc ):
                count = count + 1
            else:
                break
        parser.comments = parser.comments[count:]
        parser.group = None

    def unknown( parser, node ):
        if node.kind.name not in parser.warned:
            print( "unknown node type " + node.kind.name )
        parser.warned.add( node.kind.name )
        return {
            'kind': 'unknown',
            'name': node.kind.name,
            'location': node.location
        }

    def decls( parser, node ):
        return list( filter( None, map( parser, node.get_children() ) ) )

    def compound( parser, node ):
        parents = []
        members = []
        for child in node.get_children():
            c = parser( child )
            if c == None:
                continue
            if c['kind'] == 'parent':
                parents.append( c )
            else:
                members.append( c )
        return { 'parents': parents, 'members': members }

    def access( parser, node ):
        a = node.access_specifier
        if a == AccessSpecifier.PUBLIC:
            return 'public'
        if a == AccessSpecifier.PROTECTED:
            return 'protected'
        if a == AccessSpecifier.PRIVATE:
            return 'private'
        return 'unknown'

    def TRANSLATION_UNIT( parser, node ):
        result = {
            'kind': 'file',
            'name': node.spelling,
            'declarations': parser.decls( node )
        }
        parser.group = None
        return result

    def NAMESPACE( parser, node ):
        comments = parser.gather_comments( node.extent.start )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'namespace',
            'name': node.spelling,
            'comments': comments,
            'declarations': parser.decls( node )
        }
        parser.skip_comments( node.extent.end )
        parser.group = prev_group
        return result

    def VAR_DECL( parser, node ):
        comments = parser.gather_comments( node.extent.start )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'variable',
            'name': node.spelling,
            'type': node.type.spelling,
            'comments': comments
        }
        parser.skip_comments( node.extent.end )
        parser.group = prev_group
        return result

    def CLASS_DECL( parser, node ):
        comments = parser.gather_comments( node.extent.start )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'class',
            'name': node.spelling,
            'comments': comments
        } | parser.compound( node )
        parser.skip_comments( node.extent.end )
        parser.group = prev_group
        return result

    def STRUCT_DECL( parser, node ):
        result = parser.CLASS_DECL( node )
        result['kind'] = 'struct'
        return result

    def CXX_BASE_SPECIFIER( parser, node ):
        result = {
            'kind': 'parent',
            'name': node.spelling,
            'access': parser.access( node )
        }
        parser.skip_comments( node.extent.end )
        return result

    def CXX_ACCESS_SPEC_DECL( parser, node ):
        # Ignore public:/protected:/private: access.
        # Each member is tagged with access already.
        comments = parser.gather_comments( node.extent.start )
        return None

    def CXX_METHOD( parser, node ):
        comments = parser.gather_comments( node.extent.start )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'method',
            'name': node.spelling,
            'comments': comments,
            'type': node.type.spelling,
            'access': parser.access( node ),
            'result': node.result_type.spelling,
            'arguments': [parser( a ) for a in node.get_arguments()],
        }
        parser.skip_comments( node.extent.end )
        parser.group = prev_group
        return result

    def CONSTRUCTOR( parser, node ):
        result = parser.CXX_METHOD( node )
        result['kind'] = 'constructor'
        return result

    def FIELD_DECL( parser, node ):
        comments = parser.gather_comments( node.extent.start )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'field',
            'name': node.spelling,
            'comments': comments,
            'type': node.type.spelling,
            'access': parser.access( node ),
        }
        parser.skip_comments( node.extent.end )
        parser.group = prev_group
        return result

    def PARM_DECL( parser, node ):
        return {
            'kind': 'param',
            'name': node.spelling,
            'type': node.type.spelling,
        }

