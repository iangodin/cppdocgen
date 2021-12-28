
import re
import markdown
import html
from pprint import pprint 

# Pygments highlight classes
hl_t = 'class="kt"' # Type
hl_f = 'class="nf"' # Function
hl_v = 'class="nv"' # Variable
hl_s = 'class="o"' # Symbol
hl_k = 'class="k"' # Keyword

class Cleanup:
    def __init__( self ):
        self.header = re.compile( r'[\s]*([^:]*)[:][\s]*' )
        self.definition = re.compile( r'[\s]*([^-]*)[-](.*)' )
        configs = {
            'markdown_blockdiag': { 'format': 'svg' }
        }
        self.md = markdown.Markdown( extensions = [
                'def_list',
                'admonition',
                'mdx_outline',
                'markdown_blockdiag',
                'pymdownx.details',
                'pymdownx.arithmatex',
                'pymdownx.superfences',
                'pymdownx.smartsymbols',
                'pymdownx.highlight',
            ], extension_configs = configs )

    def __call__( self, node ):
        if 'declarations' in node:
            for n in node['declarations']:
                self( n )
        if 'members' in node:
            for n in node['members']:
                self( n )
        if 'group' in node:
            for n in node['group']:
                self( n )
        if 'friend' in node:
            self( node['friend'] )

        lines = []
        if 'comments' in node:
            for c in node['comments']:
                if c.startswith( '///<' ):
                    lines.append( c[4:] )
                elif c.startswith( '///' ):
                    lines.append( c[3:] )
                elif c.startswith( '/**<' ):
                    lines = lines + c[4:-2].splitlines()
                elif c.startswith( '/**' ):
                    lines = lines + c[3:-2].splitlines()
                elif c.startswith( '/*!<' ):
                    lines = lines + c[3:-2].splitlines()
                elif c.startswith( '/*!' ):
                    lines = lines + c[3:-2].splitlines()
                else:
                    assert False, 'unknown comment: ' + c
            lines = self.normalize_spaces( lines )
            lines = self.simple_headers( lines )
            lines = self.simple_definition( lines )

        node['markdown'] = lines
        node['html'] = self.md.convert( '\n'.join( lines ) ).splitlines()

        display = getattr( self, 'display_' + node['kind'], self.display_default )
        node['description'] = display( node )

    def count_leading_spaces( self, line ):
        return len( line ) - len( line.lstrip( ' ' ) )

    def normalize_spaces( self, lines ):
        # Replace tabs with 4 spaces
        min_spaces = 9999
        for i in range( len( lines ) ):
            line = lines[i]
            line.replace( '\t', '    ' )
            lines[i] = line
            if not ( line.isspace() or len( line ) == 0 ):
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

    def html_type( self, tname, width = 0 ):
        result = ''
        if len( tname ) != 0:
            tname = html.escape( tname.rjust( width ) )
            result = f'<span {hl_t}>{tname}</span> '
        return result 

    def html_func( self, name ):
        result = f'<span {hl_f}>{name}</span> '
        return result 

    def html_var( self, name ):
        result =  f'<span {hl_v}>{name}</span> '
        return result 

    def html_symbol( self, sym ):
        sym = html.escape( sym )
        result =  f'<span {hl_v}>{sym}</span> '
        return result 

    def html_class( self, name ):
        result =  f'<span {hl_k}>class</span> <span {hl_t}>{name}</span> '
        return result 

    def html_arg( self, arg, argwidth = 0 ):
        atype = self.html_type( arg['type'], argwidth )
        aname = self.html_var( arg['name'] )
        return f'{atype}{aname}'

    def html_template( self, tmps ):
        result = []
        if tmps != None:
            if len( tmps ) == 0:
                result.append( f'<span {hl_k}>template</span> <span {hl_s}>&lt;&gt;</span>' )
            else:
                tmpwidth = 4 + max( [len(t['type']) for t in tmps] )
                result.append( f'<span {hl_k}>template</span> <span {hl_s}>&lt;</span>' )
                for t in tmps:
                    ttype = self.html_type( t['type'], tmpwidth )
                    tname = self.html_var( t['name'] )
                    result.append( f'{ttype} {tname},' )
                result[-1].rstrip( ',' )
                result.append( f'<span {hl_s}>&gt;</span>' )
        return result

    def display_constructor( self, method ):
        return self.display_method( method )

    def display_destructor( self, method ):
        return self.display_method( method )

    def display_method( self, method ):
        name = self.html_func( method['name'] )
        args = method['arguments']
        result = self.html_type( method['result'] )

        new_lines = []
        new_lines.append( r'<div class="highlight"><pre>' )
        if len( args ) == 0 :
            new_lines.append( f'<code>{result}{name}<span {hl_s}>(</span> <span>void</span> <span {hl_s}>);</span>' )
        else:
            new_lines.append( f'<code>{result}{name}<span {hl_s}>(</span>' )
            argwidth = 4 + max( [ len( a['type'] ) for a in args] )
            for arg in args:
                new_lines.append( self.html_arg( arg, argwidth ) )
            new_lines.append( f'<span {hl_s}>);</span>' )
        new_lines.append( r'</pre></code></div>' )
        return new_lines

    def display_variable( self, var ):
        name = self.html_var( var['name'] )
        result = self.html_type( var['type'] )
        new_lines = []
        new_lines.append( r'<div class="highlight"><pre>' )
        new_lines.append( f'<code>{result} {name}<span {hl_s}>;</span>' )
        new_lines.append( r'</pre></code></div>' )
        return new_lines

    def display_friend( self, friend ):
        return friend['friend']['html']

    def display_field( self, field ):
        return self.display_variable( field )

    def display_function( self, fn ):
        new_lines = [ r'<div class="highlight"><pre>' ]

        result = self.html_type( fn['result'] )

        new_lines += self.html_template( fn.get( 'templates', None ) )

        name = self.html_func( fn['name'] )
        args = fn['arguments']
        if len( args ) == 0 :
            new_lines.append( f'{result}{name}<span {hl_s}>(</span> <span>void</span> <span {hl_s}>);</span>' )
        else:
            new_lines.append( f'{result}{name}<span {hl_s}>(</span>' )
            argwidth = 4 + max( [ len( a['type'] ) for a in args] )
            for arg in args:
                new_lines.append( self.html_arg( arg, argwidth ) )
            new_lines.append( f'<span {hl_s}>);</span>' )
        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

    def display_class( self, cls ):
        new_lines = [ r'<div class="highlight"><pre>' ]
        new_lines += self.html_template( cls.get( 'templates', None ) )
        new_lines.append( self.html_class( cls['name'] ) + self.html_symbol( ';' ) )
        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

    def display_type( self, typ ):
        name = typ['name']
        result = typ['type']
        new_lines = []
        new_lines.append( r'``` {.cpp}' )
        new_lines.append( f'{result};' )
        new_lines.append( r'```' )
        return new_lines

    def display_typedef( self, typedef ):
        name = typedef['name']
        result = typedef['type']
        new_lines = []
        new_lines.append( '``` {.cpp}' )
        new_lines.append( f'using {name} = {result};' )
        new_lines.append( r'```' )
        return new_lines
