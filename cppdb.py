
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
        self.cursor.execute( 'CREATE TABLE IF NOT EXISTS nodes ( id INTEGER PRIMARY KEY, parent_id INTEGER, kind VARCHAR(64), name VARCHAR(64), link VARCHAR(64), html TEXT, UNIQUE( parent_id, name, kind ) );' )

    def write( self, node, parent_id = 0 ):
        if node.get( 'access', 'public' ) == 'private':
            if len( node['html'] ) == 0:
                return

        kind = node['kind']
        name = node['name']
        link = node['link']
        html = '\n'.join( node['html'] ) if 'html' in node else [ '<p>Documentatin Missing</p>' ]
        html = '\n'.join( node['description'] ) + html
        idsel = f'SELECT id FROM nodes WHERE parent_id={parent_id} AND name="{name}" AND kind="{kind}"'
        self.cursor.execute( f'INSERT OR REPLACE INTO nodes ( id, parent_id, kind, name, link, html ) VALUES ( ({idsel}), ?, ?, ?, ?, ? );', ( parent_id, kind, name, link, html ) )
        newid = self.cursor.lastrowid
        if kind == 'file':
            for n in node['declarations']:
                self.write( n, 0 )
        elif kind == 'namespace':
            for n in node['declarations']:
                self.write( n, newid )
        elif kind == 'group':
            for n in node['group']:
                self.write( n, newid )
        elif kind == 'class':
            for n in node['members']:
                self.write( n, newid )
        elif kind == 'struct':
            for n in node['members']:
                self.write( n, newid )
