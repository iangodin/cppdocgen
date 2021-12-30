
import sqlite3

class CPPDatabase:
    def __init__( self, dbfile ):
        self.connection = sqlite3.connect( dbfile )
        self.cursor = self.connection.cursor()
        self.create_table()

    def close( self ):
        self.connection.commit()
        self.connection.close()

    def create_table( self ):
        self.cursor.execute( 'CREATE TABLE IF NOT EXISTS nodes ( id INTEGER PRIMARY KEY, parent_id INTEGER, kind VARCHAR(64), name VARCHAR(64), link VARCHAR(64), user TEXT, auto TEXT );' )

    def write( self, node, parent_id = 0 ):
        if node.get( 'access', 'public' ) == 'private':
            if len( node['html'] ) == 0:
                return

        kind = node['kind']
        name = node['name']
        link = str( node['link'] )
        user = '\n'.join( node['user_doc'] ) if 'user_doc' in node else '<p>Documentation Missing</p>'
        auto = '\n'.join( node['auto_doc'] ) if 'auto_doc' in node else '<p>Documentation Missing</p>'
        self.cursor.execute( f'INSERT OR FAIL INTO nodes ( parent_id, kind, name, link, user, auto ) VALUES ( ?, ?, ?, ?, ?, ? );', ( parent_id, kind, name, link, user, auto ) )
        newid = self.cursor.lastrowid
        if 'children' in node:
            for n in node['children']:
                self.write( n, newid )
