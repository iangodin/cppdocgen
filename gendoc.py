
import re

header = re.compile( r'[\s]*([^:]*)[:][\s]*' )
definition = re.compile( r'[\s]*([^-]*)[-](.*)' )

class DocGenerator:
    def __init__( self ):
        self.tabs = 4
        self.in_definition = False

    def beginning_spaces( self, line ):
        count = 0
        for c in line:
            if c == ' ':
                count = count + 1
            elif c == '\t':
                count = count + self.tabs
            else:
                break
        return count

    def __call__( self, lines, indent = 0 ):
        result = ''

        if len( lines ) == 0:
            return ( result, None )

        line = lines[0]
        spaces = self.beginning_spaces( line )
        if spaces <= indent:
            return ( result, lines )

        match = header.fullmatch( line )
        if match:
            result = result + '<section>\n'
            result = result + '<h1>' + match.group( 1 ) + '</h1>\n'
            ( html, rest ) = self( lines[1:], spaces )
            result = result + html
            result = result + '</section>\n'
            return ( result, rest )

        match = definition.fullmatch( line )
        if match:
            in_def = self.in_definition
            self.in_definition = True
            if not in_def:
                result = result + '<dl>\n'

            result = result + '<dt>' + match.group(1) + '</dt>\n'
            result = result + '<dd>\n'
            extra_line = ( ' ' * spaces ) + match.group(2)
            ( html, rest ) = self( [extra_line] + lines[1:], spaces )
            result = result + html
            result = result + '</dd>\n'
            self.in_definition = in_def
            if not in_def:
                result = result + '</dl>\n'
            return ( result, rest )

        result = result + '<p>\n'
        result = result + line + '\n'
        count = 1
        while count < len( lines ) and self.beginning_spaces( lines[count] ) >= spaces:
            result = result + line + '\n'
            count = count + 1
        result = result + '</p>\n'
        return ( result, lines[count:] )






