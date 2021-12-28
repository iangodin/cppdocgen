
import re
import markdown
from pprint import pprint 

class Cleanup:
    def __init__( self ):
        self.header = re.compile( r'[\s]*([^:]*)[:][\s]*' )
        self.definition = re.compile( r'[\s]*([^-]*)[-](.*)' )
        configs = {
            'markdown_blockdiag': { 'format': 'svg' }
        }
        self.md = markdown.Markdown( extensions = [
                'def_list',
                'markdown_blockdiag',
                'pymdownx.details',
                'pymdownx.arithmatex',
                'pymdownx.superfences',
                'pymdownx.smartsymbols',
                'pymdownx.highlight',
            ], extension_configs = configs )

    def __call__( self, node ):
        lines = []
        if 'comments' in node:
            for c in node['comments']:
                if c.startswith( '//' ):
                    lines.append( c[2:] )
                elif c.startswith( '/*' ):
                    lines = lines + c[2:-2].splitlines()
                else:
                    assert False, 'unknown comment: ' + c

        lines = self.normalize_spaces( lines )
        lines = self.simple_headers( lines )
        lines = self.simple_definition( lines )

        display = getattr( self, 'display_' + node['kind'], self.display_default )
        lines = display( node ) + lines

        node['markdown'] = lines
        node['html'] = self.md.convert( '\n'.join( lines ) ).splitlines()

        if 'declarations' in node:
            for n in node['declarations']:
                self( n )
        if 'members' in node:
            for n in node['members']:
                self( n )
        if 'group' in node:
            for n in node['group']:
                self( n )

    def count_leading_spaces( self, line ):
        return len( line ) - len( line.lstrip( ' ' ) )

    def normalize_spaces( self, lines ):
        # Replace tabs with 4 spaces
        min_spaces = 9999
        for i in range( len( lines ) ):
            line = lines[i]
            line.replace( '\t', '    ' )
            lines[i] = line
            if not line.isspace():
                min_spaces = min( min_spaces, self.count_leading_spaces( line ) )

        for i in range( len( lines ) ):
            line = lines[i]
            if line.isspace():
                line = ''
            else:
                line = line[min_spaces:]
            lines[i] = line
        return lines

    def simple_headers( self, lines ):
        for i in range( len( lines ) ):
            line = lines[i]
            match = self.header.fullmatch( line )
            if match:
                line = '#### ' + match.group( 1 ).strip()
            lines[i] = line
        return lines

    def simple_definition( self, lines ):
        new_lines = []
        for line in lines:
            match = self.definition.fullmatch( line )
            if match:
                new_lines.append( '' )
                new_lines.append( match.group( 1 ).strip() )
                new_lines.append( ':  ' + match.group( 2 ).strip() )
            else:
                new_lines.append( line )
        return new_lines

    def display_default( self, node ):
        return []

    def display_unknown( self, node ):
        kind = node['kind'].title()
        name = node['name']
        info = node['info']
        file = str( node['location'].file )
        lineno = str( node['location'].line )
        new_lines = []
        new_lines.append( f'Defined in {file} at line {lineno}.' )
        new_lines.append( '' )
        new_lines.append( f'It\'s a kind of {info}.' )
        return new_lines

    def display_constructor( self, method ):
        kind = method['kind'].title()
        name = method['name']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        args = method['arguments']
        if len( args ) == 0 :
            new_lines.append( f'{name} ();' )
        else:
            new_lines.append( f'{name} (' )
            argwidth = 4 + max( [ len( a['type'] ) for a in method['arguments'] ] )
            for arg in method['arguments']:
                new_lines.append( arg['type'].rjust( argwidth, ' ' ) + ' ' + arg['name'] )
            new_lines.append( ');' )
        new_lines.append( r'```' )
        return new_lines

    def display_destructor( self, method ):
        kind = method['kind'].title()
        name = method['name']
        result = method['result']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        new_lines.append( f'{name} ();' )
        new_lines.append( r'```' )
        return new_lines

    def display_method( self, method ):
        kind = method['kind'].title()
        name = method['name']
        result = method['result']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        args = method['arguments']
        if len( args ) == 0 :
            new_lines.append( f'{result} {name} ();' )
        else:
            new_lines.append( f'{result} {name} (' )
            argwidth = 4 + max( [ len( a['type'] ) for a in args] )
            for arg in args:
                new_lines.append( arg['type'].rjust( argwidth, ' ' ) + ' ' + arg['name'] )
            new_lines.append( ');' )
        new_lines.append( r'```' )
        return new_lines

    def display_variable( self, method ):
        kind = method['kind'].title()
        name = method['name']
        result = method['type']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        new_lines.append( f'{result} {name};' )
        new_lines.append( r'```' )
        return new_lines


    def display_field( self, method ):
        kind = method['kind'].title()
        name = method['name']
        result = method['type']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        new_lines.append( f'{result} {name};' )
        new_lines.append( r'```' )
        return new_lines

    def display_function( self, fn ):
        kind = fn['kind'].title()
        name = fn['name']
        tmps = fn['templates'] if 'templates' in fn else None
        result = fn['result']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        if tmps != None:
            if len( tmps ) == 0:
                new_lines.append( f'template <>' )
            else:
                tmpwidth = 4 + max( [len(t['type']) for t in tmps] )
                new_lines.append( f'template < ' )
                for t in tmps:
                    new_lines.append( t['type'].rjust( tmpwidth, ' ' ) + ' ' + t['name'] )
                new_lines.append( f'>' )
        args = fn['arguments']
        if len( args ) == 0 :
            new_lines.append( f'{result} {name} ();' )
        else:
            new_lines.append( f'{result} {name} (' )
            argwidth = 4 + max( [ len( a['type'] ) for a in args] )
            for arg in args:
                new_lines.append( arg['type'].rjust( argwidth, ' ' ) + ' ' + arg['name'] )
            new_lines.append( ');' )
        new_lines.append( r'```' )
        return new_lines

    def display_class( self, fn ):
        kind = fn['kind'].title()
        name = fn['name']
        tmps = fn['templates'] if 'templates' in fn else None
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        if tmps != None:
            if len( tmps ) == 0:
                new_lines.append( f'template <>' )
            else:
                tmpwidth = 4 + max( [len(t['type']) for t in tmps] )
                new_lines.append( f'template < ' )
                for t in tmps:
                    new_lines.append( t['type'].rjust( tmpwidth, ' ' ) + ' ' + t['name'] )
                new_lines.append( f'>' )
        new_lines.append( f'class {name};' )
        new_lines.append( r'```' )
        return new_lines

    def display_typedef( self, typedef ):
        kind = typedef['kind'].title()
        name = typedef['name']
        result = typedef['type']
        new_lines = []
        new_lines.append( '``` {.cpp .linenums=1}' )
        new_lines.append( f'using {name} = {result};' )
        new_lines.append( r'```' )
        return new_lines
