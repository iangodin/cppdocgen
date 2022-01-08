
import sqlite3

class CPPDatabase:
    def __init__( self, dbfile ):
        self.connection = sqlite3.connect( dbfile )
        self.cursor = self.connection.cursor()
        self.create_tables()

    def close( self ):
        self.connection.commit()
        self.connection.close()

    def create_tables( self ):
        self.cursor.execute( '''CREATE TABLE IF NOT EXISTS nodes (
                name VARCHAR(64),
                link VARCHAR(64),
                parent VARCHAR(64),
                kind VARCHAR(64),
                decl TEXT,
                comments TEXT
            );''' )

    def insert_records( self, nodes ):
        for ( link, node ) in nodes.items():
            if node.get( 'access', 'public' ) == 'private':
                if len( node['comments'] ) == 0:
                    return
            name = node['name']
            parent = node['parent']
            kind = node['kind']
            decl = node['decl']
            cmts = '\n'.join( node['comments'] )

            self.cursor.execute(
                'INSERT OR FAIL INTO nodes ( name, link, parent, kind, decl, comments ) ' +
                    'VALUES ( ?, ?, ?, ?, ?, ? );',
                    ( name, link, parent, kind, decl, cmts ) )
