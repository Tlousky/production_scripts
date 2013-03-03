bl_info = {    
    "name"        : "Armature parenting tree generator",
    "author"      : "Tamir Lousky",
    "version"     : (1, 0, 0),
    "blender"     : (2, 66, 0),
    "category"    : "Rigging",
    "wiki_url"    : "https://github.com/Tlousky/production_scripts/wiki/_new?wiki[name]=draw_parenting_tree.py",
    "download_url": "https://github.com/Tlousky/production_scripts/blob/master/draw_parenting_tree.py",
    "description" : "Creates a node tree representing the armature's bone parenting structure."
    }

import bpy

def create_node( bone, x, y, row ):
    """ recursive function that creates a math node for each bone in the armature
    and draws connections between the bones (math nodes) and their parents """

    node = tree.nodes.new('MATH') # create a new math node

    # set up node location, label and name, and minimize (hide) the node
    node.location = x,y
    node.label    = bone.name
    node.name     = bone.name
    node.hide     = True

    # if this isn't the (parentless) root bone, create a link to its parent
    if bone.parent:
        parent_name = bone.parent.name
        parent_node = tree.nodes[parent_name]
        links.new( parent_node.outputs[0], node.inputs[0] )
    
    # iterate over all the current's bone's children and draw their nodes
    row += 1 # the row represents each "generation" visually via x axis distance
    for child in bone.children:
        x = 200 * row
        y = 0
        create_node( child, x, y, row )

def set_node_height( linksnode, i, yp ):
    """ recurse all nodes and set their height
    according to the parenting structure """
    print( linksnode, "I: ", i, "yp: ", yp )
    n = len(node.outputs[0].links) # count the number of children
    y = yp + (i + n) * -30         # calculate y value according to: parent's y value,
                                   # no. of children and the position of current bone in children
    node.location.y = y            # set the node's actual y location value
    
    j = 0
    for link in node.outputs[0].links: # iterate current node's links
        child = link.to_node           # reference output node
        j += 1
        set_node_height( child, j, y )

if not bpy.context.scene.use_nodes:
    print( 'can only draw tree if you are using nodes in the rendering compositor' )
else:
    rig   = bpy.context.object  # reference the selected armature
    bones = rig.data.bones      # reference bone data

    # find root bone
    root = ''
    for bone in bones:
        if not bone.parent:     # the root bone has no parent
            root = bone.name

    # create references to node tree and node links
    tree  = bpy.context.scene.node_tree
    links = tree.links

    # clear existing nodes
    for n in tree.nodes:
        tree.nodes.remove(n)

    # create root node's location
    (row, x, y) = (0, 0, 0)

    # Draw primary tree (starting from root bone)
    create_node( bones[root], x, 0, row )

    # iterate over all nodes and adjust their y value
    i = 0
    for node in tree.nodes:
        set_node_height( node, i, 0 )
        i += 1