
import re
import markdown
import html
from functools import reduce
from pprint import pprint 

htmlTypes = [ 'global', 'class', 'struct', 'namespace' ]

# Pygments highlight classes
hl_t = 'class="kt"' # Type
hl_n = 'class="nt"' # Tag
hl_f = 'class="nf"' # Function
hl_c = 'class="nc"' # Class
hl_v = 'class="nv"' # Variable
hl_s = 'class="o"' # Symbol
hl_k = 'class="k"' # Keyword

class Cleanup:
    def __init__( self ):
        self.header = re.compile( r'[\s]*([^:]*)[:][\s]*' )
        self.definition = re.compile( r'[\s]*((?!=>).+)=>(.*)' )
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

    def __call__( cleaner, node ):
        mdown = cleaner.generate_markdown( node )

        node['user_doc'] = cleaner.md.convert( '\n'.join( mdown ) ).splitlines()

        display = getattr( cleaner, 'display_' + node['kind'], cleaner.display_default )
        node['auto_doc'] = display( node )

        # Keep the children at the end of the node dictionary
        if 'children' in node:
            c = node['children']
            del node['children']
            node['children'] = c

    def generate_markdown( cleaner, node ):
        lines = []
        if 'comments' in node:
            for c in node['comments']:
                if c == len(c) * '/':
                    pass
                elif c.startswith( '///<' ):
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
            lines = cleaner.normalize_spaces( lines )
            lines = cleaner.simple_headers( lines )
            lines = cleaner.simple_definition( lines )
        return lines

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

    def html_type_space( self, tname, width = 0 ):
        result = ''
        if len( tname ) != 0:
            tname = html.escape( tname.rjust( width ) )
            result = f'<span {hl_t}>{tname}</span> '
        return result 

    def html_type( self, tname, width = 0 ):
        result = ''
        if len( tname ) != 0:
            tname = html.escape( tname.rjust( width ) )
            result = f'<span {hl_t}>{tname}</span>'
        return result 

    def html_tag( self, tname ):
        tname = html.escape( tname )
        result = f'<span {hl_n}>{tname}</span>'
        return result 

    def html_func( self, name ):
        result = f'<span {hl_f}>{name}</span>'
        return result 

    def html_var( self, name ):
        result =  f'<span {hl_v}>{name}</span>'
        return result 

    def html_symbol( self, sym ):
        sym = html.escape( sym )
        result =  f'<span {hl_v}>{sym}</span>'
        return result 

    def html_class( self, name ):
        result =  f'<span {hl_k}>class</span> <span {hl_c}>{name}</span>'
        return result 

    def html_struct( self, name ):
        result =  f'<span {hl_k}>struct</span> <span {hl_c}>{name}</span>'
        return result 

    def html_arg( self, arg, argwidth = 0 ):
        atype = self.html_type_space( arg['type'], argwidth )
        aname = self.html_var( arg['name'] )
        return f'{atype}{aname},'

    def html_params( self, params ):
        if len( params ) == 0 :
            return '<span {hl_s}>(</span> <span {hl_k}>void</span> <span {hl_s}>);</span>'
        elif len( params ) == 1 :
            param = self.html_arg( params[0] ).rstrip( ',' )
            return f'<span {hl_s}>(</span> {param} <span {hl_s}>);</span>'
        else:
            lines = []
            lines.append( f'<span {hl_s}>(</span>' )
            argwidth = 4 + max( [ len( a['type'] ) for a in params] )
            for arg in params:
                lines.append( self.html_arg( arg, argwidth ) )
            lines[-1] = lines[-1].rstrip( ',' ) + f' <span {hl_s}>);</span>'
            return '\n'.join( lines )

    def html_template_param( self, param, tmpwidth = 0 ):
        ttype = self.html_type_space( param['type'], tmpwidth )
        tname = self.html_var( param['name'] )
        return f'{ttype}{tname},'

    def html_template( self, tmps ):
        result = []
        if tmps != None:
            if len( tmps ) == 0:
                result.append( f'<span {hl_k}>template</span> <span {hl_s}>&lt;&gt;</span>' )
            elif len( tmps ) == 1:
                tparam = self.html_template_param( tmps[0] ).rstrip( ',' )
                result.append( f'<span {hl_k}>template</span> <span {hl_s}>&lt;</span> {tparam} <span {hl_s}>&gt;</span>' )
            else:
                tmpwidth = 4 + max( [len(t['type']) for t in tmps] )
                result.append( f'<span {hl_k}>template</span> <span {hl_s}>&lt;</span>' )
                for t in tmps:
                    result.append( self.html_template_param( t, tmpwidth ) )
                result[-1] = result[-1].rstrip( ',' ) + ' <span {hl_s}>&gt;</span>'
        return result

    def display_constructor( self, method ):
        return self.display_method( method )

    def display_destructor( self, method ):
        return self.display_method( method )

    def display_method( self, method ):
        return self.display_function( method )

    def display_variable( self, var ):
        name = self.html_var( var['name'] )
        result = self.html_type_space( var['type'] )
        new_lines = []
        new_lines.append( r'<div class="highlight"><pre>' )
        new_lines.append( f'<code>{result}{name}<span {hl_s}>;</span>' )
        new_lines.append( r'</pre></code></div>' )
        return new_lines

    def display_friend( self, friend ):
        return friend['friend']['html']

    def display_field( self, field ):
        return self.display_variable( field )

    def display_function( self, fn ):
        result = self.html_type_space( fn['result'] )
        name = self.html_func( fn['name'] )
        line = f'<code>{result}{name}'
        line += self.html_params( fn['params'] )

        new_lines = []
        new_lines.append( r'<div class="highlight"><pre>' )
        new_lines += self.html_template( fn.get( 'templates', None ) )
        new_lines += line.splitlines()
        new_lines.append( r'</code></pre></div>' )
        return new_lines

    def display_class( self, cls ):
        new_lines = [ r'<div class="highlight"><pre>' ]
        new_lines += self.html_template( cls.get( 'templates', None ) )
        new_lines.append( self.html_class( cls['name'] ) + self.html_symbol( ';' ) )

        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

    def display_struct( self, cls ):
        new_lines = [ r'<div class="highlight"><pre>' ]
        new_lines += self.html_template( cls.get( 'templates', None ) )
        new_lines.append( self.html_struct( cls['name'] ) + self.html_symbol( ';' ) )

        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

    def display_type( self, typ ):
        new_lines = [ r'<div class="highlight"><pre>' ]

        result = self.html_type( typ['type'] )
        new_lines.append( f'{result};' )

        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

    def display_typedef( self, typedef ):
        new_lines = [ r'<div class="highlight"><pre>' ]

        name = self.html_tag( typedef['name'] )
        result = self.html_type( typedef['type'] )
        new_lines.append( f'<span {hl_k}>using</span> {name} = {result};' )

        new_lines.append( r'</pre></code></div>' )
        new_lines[2] = '<code>' + new_lines[2]
        return new_lines

