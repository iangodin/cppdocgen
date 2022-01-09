
import sqlite3
from pprint import pprint

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
                kind VARCHAR(64),
                key VARCHAR(128),
                link VARCHAR(128),
                parent VARCHAR(128),
                decl TEXT,
                comments TEXT
            );''' )

    def insert_records( self, nodes ):
        for node in nodes:
            if node['name'] == '':
                continue
            link = node['link']
            if '#' in link:
                link = link.replace( '#', '.html#' )
            elif '?' in link:
                link = link.replace( '?', '.html?' )
            else:
                link = link + '.html'
            if node.get( 'access', 'public' ) == 'private':
                if len( node['comments'] ) == 0:
                    continue
            name = node['name']
            parent = '/'.join( node['key'][:-1] )
            key = '/'.join( node['key'] )
            kind = node['kind']
            decl = node['decl']
            cmts = '\n'.join( node['comments'] )

            self.cursor.execute(
                'INSERT OR FAIL INTO nodes ( name, kind, key, link, parent, decl, comments ) ' +
                    'VALUES ( ?, ?, ?, ?, ?, ?, ? );',
                    ( name, kind, key, link, parent, decl, cmts ) )
        for node in nodes:
            self.insert_records( node['children'] )
