
import sqlite3
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

def filter_kind( nodes, kind ):
    return filter( lambda n: n['kind'] == kind, nodes )

class HTMLGenerator:
    def __init__( self, dbfile, topdir ):
        self.topdir = topdir
        self.connection = sqlite3.connect( dbfile )
        self.cursor = self.connection.cursor()
        self.env = Environment(
            loader = FileSystemLoader( "templates" )
        )
        self.env.filters['filter_kind'] = filter_kind
        self.env.globals['list'] = list

    def generate( self ):
        node = { 'id': 0, 'name': 'global', 'kind': 'global', 'html': '' }
        self.gather_children( node )
        self.generate_node( node, Path() )

    def gather_children( self, node ):
        parent_id = node['id']
        rows = self.cursor.execute( f'SELECT id, name, kind, html FROM nodes WHERE parent_id={parent_id} AND kind != "file" ORDER BY id;' ).fetchall();
        children = []
        for row in rows:
            child = { 'id': row[0], 'name': row[1], 'kind': row[2], 'html': row[3] }
            self.gather_children( child )
            children.append( child )
        node['children'] = children

    def generate_node( self, node, parent ):
        if node['kind'] in [ 'class', 'namespace', 'global' ]:
            filename = self.topdir / parent / ( node['name'] + '.html' )
            filename.parent.mkdir( parents = True, exist_ok = True )
            template = self.env.get_template( node['kind'] + ".html" )
            htmlData = template.render( node=node, parents=parent.parts );
            with filename.open( 'w' ) as f:
                f.write( htmlData )

        iterate = getattr( self, 'gen_' + node['kind'], None )
        if iterate:
            iterate( node, parent )

    def gen_global( self, node, parent ):
        pathname = parent / node['name']
        for n in node['children']:
            self.generate_node( n, pathname )

    def gen_namespace( self, node, parent ):
        pathname = parent / node['name']
        for n in node['children']:
            self.generate_node( n, pathname )
