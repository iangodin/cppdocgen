
from pathlib import Path

class LinkUp:
    def __init__( self ):
        self.links = {}

    def __call__( self, node, url = Path() ):
        kind = node['kind']
        link = getattr( self, 'link_' + kind, self.link_default )
        newurl = link( node, url )
        node['link'] = str( newurl )
        self.fill_links( node, Path( url ) )

    def fill_links( self, node, path ):
        pass

    def link_default( self, node, parent ):
        return str( parent ) + '.html#' + node['name']

    def link_class( self, node, parent ):
        result = parent / ( node['name'] + '.html' )
        for n in node['members']:
            self( n, result.with_suffix( '' ) )
        return result

    def link_struct( self, node, parent ):
        result = parent / ( node['name'] + '.html' )
        for n in node['members']:
            self( n, result.with_suffix( '' ) )
        return result

    def link_namespace( self, node, parent ):
        result = parent / ( node['name'] + '.html' )
        for n in node['declarations']:
            self( n, result.with_suffix( '' ) )
        return result

    def link_group( self, node, parent ):
        for n in node['group']:
            self( n, parent )
        return parent

    def link_file( self, node, parent ):
        assert str( parent ) == '.', 'expected file parent to be empty, got ' + str( parent )
        result = Path( 'index.html' )
        for n in node['declarations']:
            self( n, parent )
        return result

