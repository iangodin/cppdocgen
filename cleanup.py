
import re
import markdown
import html
from functools import reduce
from pprint import pprint 

htmlTypes = [ 'global', 'class', 'struct', 'namespace' ]

doxy_class = re.compile( r'[\s]*@class .*' )
doxy_brief = re.compile( r'[\s]*@brief(.*)' )
doxy_param = re.compile( r'[\s]*@param[\s]+([\w]+)[\s]*(.*)' )

def doxy_filter( lines ):
    found_param = False
    result = []
    for line in lines:
        match = doxy_brief.match( line )
        if match:
            result.append( match.group( 1 ) )
            result.append( '' )
            continue
        match = doxy_class.match( line )
        if match:
            continue
        match = doxy_param.match( line )
        if match:
            if not found_param:
                result.append( 'Parameters:' )
                found_param = True
            result.append( '  ' + match.group( 1 ) + ' => ' + match.group( 2 ) )
            continue
        result.append( line )
    return result

class Cleanup:
    def __init__( self ):
        self.header = re.compile( r'[\s]*([^:]*)[:][\s]*' )
        self.definition = re.compile( r'[\s]*((?!=>).+)=>(.*)' )
        configs = {
            'markdown_blockdiag': { 'format': 'svg' },
            'pymdownx.highlight': { 'use_pygments': False },
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

    def __call__( cleaner, cmts ):
        if cmts == '':
            return cmts
        clean = cleaner.cleanup_comments( cmts.splitlines() )
        doxy = doxy_filter( clean )
        mdown = cleaner.convert_to_markdown( doxy )
        mdhtml = cleaner.md.convert( '\n'.join( mdown ) )
        #pprint( ( cmts, clean, doxy, mdown, mdhtml ) )
        return mdhtml

        #display = getattr( cleaner, 'display_' + node['kind'], cleaner.display_default )
        #node['auto_doc'] = cleaner.md.convert( '\n'.join( display( node ) ) ).splitlines()

        # Keep the children at the end of the node dictionary
        #if 'children' in node:
        #    c = node['children']
        #    del node['children']
        #    node['children'] = c

    def cleanup_comments( cleaner, lines ):
        lines = cleaner.normalize_spaces( lines )
        return lines

    def convert_to_markdown( cleaner, lines ):
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
            tname = tname.rjust( width )
            result = f'{tname} '
        return result 

    def html_type( self, tname, width = 0 ):
        result = ''
        if len( tname ) != 0:
            tname = tname.rjust( width )
            result = f'{tname}'
        return result 

    def html_class( self, name ):
        result =  f'class {name}'
        return result 

    def html_struct( self, name ):
        result =  f'struct {name}'
        return result 

    def html_arg( self, arg, argwidth = 0 ):
        atype = self.html_type_space( arg['type'], argwidth )
        aname = arg['name']
        return f'{atype}{aname},'

    def html_params( self, params ):
        if len( params ) == 0 :
            return '( void )'
        elif len( params ) == 1 :
            param = self.html_arg( params[0] ).rstrip( ',' )
            return f'( {param} )'
        else:
            lines = []
            lines.append( f'(>' )
            argwidth = 4 + max( [ len( a['type'] ) for a in params] )
            for arg in params:
                lines.append( self.html_arg( arg, argwidth ) )
            lines[-1] = lines[-1].rstrip( ',' ) + f' )'
            return '\n'.join( lines )

    def html_template_param( self, param, tmpwidth = 0 ):
        ttype = self.html_type_space( param['type'], tmpwidth )
        tname = param['name']
        return f'{ttype}{tname},'

    def html_template( self, tmps ):
        result = []
        if tmps != None:
            if len( tmps ) == 0:
                result.append( f'template <>' )
            elif len( tmps ) == 1:
                tparam = self.html_template_param( tmps[0] ).rstrip( ',' )
                result.append( f'template < {tparam} >' )
            else:
                tmpwidth = 4 + max( [len(t['type']) for t in tmps] )
                result.append( f'template <' )
                for t in tmps:
                    result.append( self.html_template_param( t, tmpwidth ) )
                result[-1] = result[-1].rstrip( ',' ) + ' >'
        return result

    def display_constructor( self, method ):
        return self.display_method( method )

    def display_destructor( self, method ):
        return self.display_method( method )

    def display_method( self, method ):
        return self.display_function( method )

    def display_variable( self, var ):
        name = var['name']
        result = self.html_type_space( var['type'] )
        new_lines = []
        new_lines.append( r'``` .cpp' )
        new_lines.append( f'{result}{name};' )
        new_lines.append( r'```' )
        return new_lines

    def display_friend( self, friend ):
        return [ friend['name'] ]

    def display_field( self, field ):
        return self.display_variable( field )

    def display_function( self, fn ):
        result = self.html_type_space( fn['result'] )
        name = fn['name']
        specifiers = ''.join( [ f' ' + s for s in fn['specifiers'] ] )
        line = f'{result}{name}'
        line += self.html_params( fn['params'] )
        line += specifiers
        if 'is_default' in fn and fn['is_default']:
            line += f' = default'
        line += f';'

        new_lines = []
        new_lines.append( r'``` .cpp' )
        new_lines += self.html_template( fn.get( 'templates', None ) )
        new_lines += line.splitlines()
        new_lines.append( r'```' )
        return new_lines

    def display_class( self, cls ):
        new_lines = [ r'``` .cpp' ]
        new_lines += self.html_template( cls.get( 'templates', None ) )
        new_lines.append( self.html_class( cls['name'] ) + ';' )

        new_lines.append( r'```' )
        return new_lines

    def display_struct( self, cls ):
        new_lines = [ r'``` .cpp' ]
        new_lines += self.html_template( cls.get( 'templates', None ) )
        new_lines.append( self.html_struct( cls['name'] ) + ';' )

        new_lines.append( r'```' )
        return new_lines

    def display_type( self, typ ):
        new_lines = [ r'``` .cpp' ]

        result = self.html_type( typ['type'] )
        new_lines.append( f'{result};' )

        new_lines.append( r'```' )
        return new_lines

    def display_typedef( self, typedef ):
        new_lines = [ r'``` .cpp' ]

        name = typedef['name']
        result = self.html_type( typedef['type'] )
        new_lines.append( f'using {name} = {result};' )

        new_lines.append( r'```' )
        return new_lines

