
import sqlite3
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

def filter_kind( nodes, kind ):
    if isinstance( kind, str ):
        return filter( lambda n: kind == '' or n['kind'] == kind, nodes )
    else:
        return filter( lambda n: n['kind'] in kind, nodes )

def anchor( node ):
    result = None
    if '#' in node['link']:
        result = node['link'].split( '#' )[-1]
    return result

toplevel = 'global'

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
        self.env.globals['anchor'] = anchor

    def generate( self ):
        node = { 'id': 0, 'name': 'global', 'kind': 'global', 'link': 'index.html', 'html': '' }
        self.gather_children( node )
        self.generate_node( node, Path() )

    def gather_children( self, node ):
        parent_id = node['id']
        rows = self.cursor.execute( f'SELECT id, name, kind, link, html FROM nodes WHERE parent_id={parent_id} AND kind != "file" ORDER BY id;' ).fetchall();
        children = []
        for row in rows:
            child = { 'id': row[0], 'name': row[1], 'kind': row[2], 'link': toplevel + '/' + row[3], 'html': row[4] }
            self.gather_children( child )
            children.append( child )
        node['children'] = children

    def generate_node( self, node, parent ):
        if node['kind'] in [ 'class', 'struct', 'namespace', 'global' ]:
            filename = self.topdir / node['link']
            assert '#' not in str( filename ), 'expected class/struct/namespace/global without fragment'
            filename.parent.mkdir( parents = True, exist_ok = True )
            template = self.env.get_template( node['kind'] + ".html" )
            htmlData = template.render( node=node, parents=parent.parts );
            with filename.open( 'w' ) as f:
                f.write( htmlData )

        iterate = getattr( self, 'gen_' + node['kind'], None )
        if iterate:
            iterate( node, parent )

    def gen_global( self, node, parent ):
        for n in node['children']:
            self.generate_node( n, parent )

    def gen_namespace( self, node, parent ):
        pathname = parent / node['name']
        for n in node['children']:
            self.generate_node( n, pathname )

    def gen_class( self, node, parent ):
        pathname = parent / node['name']
        for n in filter( lambda n : n['kind'] in ['class','struct'], node['children'] ):
            self.generate_node( n, pathname )

    def gen_struct( self, node, parent ):
        # Identical to class
        self.gen_class( node, parent )

