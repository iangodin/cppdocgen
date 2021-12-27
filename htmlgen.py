
from jinja2 import Environment, FileSystemLoader, select_autoescape

class HTMLGenerator:
    def __init__( self, topdir ):
        self.topdir = topdir
        self.env = Environment(
            loader = FileSystemLoader( "templates" )
        )

    def __call__( self, node, parent = "namespaces" ):
        if node['kind'] != 'file':
            filename = self.topdir / parent / ( node['name'] + '.html' )
            print( "FILENAME: " + str( filename ) )
            print( "PARENT: " + str( parent ) )
            filename.parent.mkdir( parents = True, exist_ok = True )
            template = self.env.get_template( node['kind'] + ".html" )
            htmlData = template.render( node=node, parent=str( parent ) );
            with filename.open( 'w' ) as f:
                f.write( htmlData )

        iterate = getattr( self, 'gen_' + node['kind'], None )
        if iterate:
            iterate( node, parent )

    def gen_file( self, node, parent ):
        pathname = parent
        for n in node['declarations']:
            self( n, pathname )

    def gen_namespace( self, node, parent ):
        pathname = parent / node['name']
        for n in node['declarations']:
            self( n, pathname )

