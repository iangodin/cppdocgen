
from decl_node import decl_node, sem_parent_list
from pprint import pprint

def create_node_from_cursor( cursor ):
    node = decl_node( cursor )

def insert_into_tree( tree, location, node ):
    if len( location ) == 1:
        for child in tree['children']:
            if child['name'] == node['name']:
                child['key'] += node['key']
                return
        tree['children'].append( node )
    else:
        parent = location[0]
        for child in tree['children']:
            if child['name'] == parent:
                insert_into_tree( child, location[1:], node )
                return;
        raise Exception( 'couldn\'t find parent ' + str( location ) )

def recurse_cursor( tree, cursor, done, files ):
    for c in cursor.get_children():
        if c in done:
            continue
        if c.kind.is_statement() or c.kind.is_expression() or c.kind.is_reference():
            continue
        done.add( c )
        if str( c.location.file.name ) in files:
            n = decl_node( c )
            parent = sem_parent_list( c )
            insert_into_tree( tree, parent, n )
            recurse_cursor( tree, c, done, files )

def gather_decls( cursor, files ):
    top = {
        'name': 'global',
        'kind': 'global',
        'key': [ cursor ],
        'comments': [],
        'children': []
    }
    recurse_cursor( top, cursor, set( [ cursor ] ), files )
    return top


