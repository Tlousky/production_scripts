# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

#
#  Author            : Tamir Lousky [ tlousky@gmail.com, tamir@pitchipoy.tv ]
#  Homepage(Wiki)    : http://bioblog3d.wordpress.com/
# 
#  Start of project              : 2013-11-08 by Tamir Lousky
#  Last modified                 : 2013-11-08
#
#  Acknowledgements 
#  ================
#  Nathan Elias (for suggesting the idea)
#  Zeffii @ StackExchange - for providing really useful insights and sample code 
#                           on how vertex colors can be matched with mesh verts.

bl_info = {    
    "name"       : "Fake HDR",
    "author"     : "Tamir Lousky",
    "version"    : (0, 0, 1),
    "blender"    : (2, 68, 0),
    "category"   : "Render",
    "location"   : "3D View >> Tools",
    "wiki_url"   : "https://github.com/Tlousky/production_scripts/wiki/Fake-HDR",
    "tracker_url": "https://github.com/Tlousky/production_scripts/blob/master/fake_hdr.py",
    "description": "Create an array of stops that mimicks an HDR image"
}

import bpy, re, bmesh
from collections import defaultdict
from mathutils   import Color

def check_poll_conditions( context ):
    hdr_image_selected = context.scene.fake_hdr_image
    rend_engine_is_bi  = context.scene.render.engine == 'BLENDER_RENDER'
    return hdr_image_selected and rend_engine_is_bi

def change_light_intensity( obj, intensity ):
    """ Change the light intensity of a lamp. Uses the correct methods to 
    affect both cycles and BI lamps """
    if bpy.context.scene.render.engine == 'CYCLES':
        if not obj.data.use_nodes:
            obj.data.use_nodes = True
        strength = obj.data.node_tree.nodes['Emission'].inputs['Strength']
        strength.default_value = intensity
    else:
        obj.data.energy = intensity

class fake_hdr(bpy.types.Panel):
    bl_idname      = "FakeHDR"
    bl_label       = "Fake HDR"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context     = 'objectmode'

    @classmethod
    def poll( self, context ):
        return True
        # return context.scene.render.engine == 'BLENDER_RENDER'

    def draw( self, context) :
        # hdr_image = context.scene.fake_hdr_image
        props     = context.scene.fake_hdr_props

        layout = self.layout
        col    = layout.column()

        col.prop_search(          
            context.scene, "fake_hdr_image",  # Pick HDR image 
            bpy.data, "images"                # From list of images in scene
        )

        col.prop( props, 'sphere_resolution' )

        layout.operator( 'render.create_hdr_sphere' )

        lbl = layout.label( "Update light array intensity and softness" )
        box = layout.box()
        col = box.column()
        lbl = col.label( "Choose control sphere to update" )

        col.prop( context.scene.fake_hdr_props, 'lamp_type'      )
        col.prop( context.scene.fake_hdr_props, 'lamp_intensity' )
        col.prop( context.scene.fake_hdr_props, 'lamp_size'      )

        
class create_hdr_sphere( bpy.types.Operator ):
    """ Create a file output node for each pass in each renderlayer """
    bl_idname      = "render.create_hdr_sphere"
    bl_label       = "Create light array"
    bl_description = "Create a light array corresponding to an HDR sphere"
    bl_options     = {'REGISTER', 'UNDO' }

    @classmethod
    def poll( self, context ):
        return check_poll_conditions( context )

    def create_sphere( self, context, subd ):
        bm = bmesh.new()
        # Create new icosphere mesh
        sphere_verts = bmesh.ops.create_icosphere( 
            bm, 
            subdivisions = subd,
            diameter = 1
         )

        # Create new mesh from bmesh
        me = bpy.data.meshes.new("LightSphere")
        bm.to_mesh(me)
        bm.free()

        # Link new object to scene
        obj = bpy.data.objects.new("LightSphere", me)
        context.scene.objects.link( obj )
        
        return obj

    def map_hdr_to_sphere( self, context, obj ):
        # Select and make active
        context.scene.objects.active = obj
        obj.select = True

        # Go to edit mode
        bpy.ops.object.mode_set(mode ='EDIT')

        # Create spherical UV map
        bpy.ops.mesh.select_all( action = 'SELECT' )
        bpy.ops.uv.sphere_project()

        # Return to object mode
        bpy.ops.object.mode_set(mode ='OBJECT')

        # Add material slot to object
        bpy.ops.object.material_slot_add()

        # Create a new material and set it up
        bpy.ops.material.new()
        mat               = bpy.data.materials[-1]
        mat.name          = 'FakeHDR.Material'
        mat.use_shadeless = True

        # Set material as active on object
        context.object.material_slots[0].material = mat
        
        # Create a new texture and set it up
        bpy.data.textures.new( name = 'FakeHDR.Texture', type = 'IMAGE' )
        tex       = bpy.data.textures[-1]
        tex.name  = 'FakeHDR.Texture'
        tex.type  = 'IMAGE'
        tex.image = bpy.data.images[ context.scene.fake_hdr_image ]

        # Add material texture slot and set it up
        mat.texture_slots.add()
        mat.texture_slots[0].texture_coords = 'UV'      # Map texture to UVs
        mat.texture_slots[0].texture        = tex

    def bake_textures_to_verts( self, context, obj ):
        # Select and make active
        context.scene.objects.active = obj
        obj.select = True

        # Set up bake textures to vert colors
        if not context.scene.render.use_bake_to_vertex_color:
            context.scene.render.use_bake_to_vertex_color = True
        if not context.scene.render.bake_type == 'TEXTURE':
            context.scene.render.bake_type = 'TEXTURE'

        # Add vertex color map
        bpy.ops.mesh.vertex_color_add()

        # Bake
        bpy.ops.object.bake_image()

    def create_lamps( self, context, obj ):
        # Select and make active
        context.scene.objects.active = obj
        obj.select = True

        # Create and reference particle system
        bpy.ops.object.particle_system_add()
        psys = obj.particle_systems['ParticleSystem']

        # Change PS type to hair
        psys.settings.type              = 'HAIR'
        psys.settings.use_advanced_hair = True

        # Emit particles regularly from the vertices of the mesh
        psys.settings.emit_from       = 'VERT'
        psys.settings.use_emit_random = False

        # Number of particles = number of verts
        psys.settings.count = len(bpy.context.object.data.vertices)

        # Change render type to duplicate objects
        psys.settings.render_type = 'OBJECT'

        # Create point light and use it as duplicate object on particle system
        bpy.ops.object.lamp_add(
            type   = 'POINT', 
            layers = (False, False, False, False, False, False, False, False, 
                      False, False, False, False, False, False, False, False, 
                      False, False, False, True)
        )

        # Reference lamp
        lampobj = bpy.context.scene.objects[ bpy.context.object.name ]
        lampname     = 'fake_hdr_lamp'
        lampobj.name = lampname

        # Lamp becomes active and selected after creation, reselect and activate icosphere
        context.scene.objects.active = obj
        obj.select = True

        # Set lamp as dupli object for particle system
        psys.settings.dupli_object = lampobj

        # Convert particle system to real lamp objects
        bpy.ops.object.duplicates_make_real()

        # Delete (now useless) original lamp
        bpy.ops.object.select_all( action = 'DESELECT' )
        lampobj.select = True
        bpy.ops.object.delete()

        # Reference all lamps
        lamps = [ o for o in bpy.context.scene.objects if lampname in o.name ]

        # Create empty which will act as the lamps' parent object
        bpy.ops.object.empty_add( type = 'SPHERE' )
        empty      = bpy.context.scene.objects[ bpy.context.object.name ]
        empty.name = 'FakeHDR.LightArray.Control'

        # Deselect all objects
        bpy.ops.object.select_all( action = 'DESELECT' )

        # Select all lamps, parent all to empty and add damped track constraints
        for lamp in lamps:
            lamp.select = True
            lamp.parent = empty

            # Create damped track constraint from lamp to empty to make sure
            # spots always look in the direction of the empty
            const = lamp.constraints.new(type='DAMPED_TRACK')
            const.target     = empty
            const.track_axis = 'TRACK_NEGATIVE_Z'

        # Make all lamp instances single users (to enable separate control
        # over their properties)
        bpy.ops.object.make_single_user(
            type   = 'SELECTED_OBJECTS', 
            object = True, 
            obdata = True
        )

        return lamps

    def color_lamps( self, context, obj, lamps ):
        vcolor_dict = defaultdict(list)
        mesh        = obj.data
        color_layer = obj.data.vertex_colors[0]

        i = 0
        for poly in mesh.polygons:
            for idx in poly.loop_indices:
                loop  = mesh.loops[idx]
                color = color_layer.data[i].color
                vcolor_dict[loop.vertex_index].append(color)
                i += 1

        avg_vcolors = {}
        for v in vcolor_dict:
            avg_vcolors[ v ] = Color( (
                sum( [ c.r for c in vcolor_dict[v] ] ) / len( vcolor_dict[v] ),
                sum( [ c.g for c in vcolor_dict[v] ] ) / len( vcolor_dict[v] ),
                sum( [ c.b for c in vcolor_dict[v] ] ) / len( vcolor_dict[v] ),
            ) )

        verts = mesh.vertices
        for v in avg_vcolors:
            lamp = [ l for l in lamps if l.location == verts[v].co ][0]
            lamp.data.color = avg_vcolors[v]

    def execute( self, context ):
        subd = context.scene.fake_hdr_props.sphere_resolution
        obj  = self.create_sphere( context, subd )
        self.map_hdr_to_sphere( context, obj )
        self.bake_textures_to_verts( context, obj )
        lamps = self.create_lamps( context, obj )
        self.color_lamps( context, obj, lamps )

        return {'FINISHED'}

class fake_HDR_props( bpy.types.PropertyGroup ):
    def update_intensity( self, context ):
        empty = context.scene.objects['FakeHDR.LightArray.Control']
        value = context.scene.fake_hdr_props.lamp_intensity

        for l in empty.children:
            change_light_intensity( l, value )

    def update_size( self, context ):
        empty = context.scene.objects['FakeHDR.LightArray.Control']
        value = context.scene.fake_hdr_props.lamp_size
        
        for l in empty.children:
            l.data.shadow_soft_size = value

    def update_type( self, context ):
        empty = context.scene.objects['FakeHDR.LightArray.Control']
        value = context.scene.fake_hdr_props.lamp_type

        for l in empty.children:
            l.data.type = str(value).upper()

    sphere_resolution = bpy.props.IntProperty(
        description = "Light sphere subdivisions",
        name        = "Sphere Resolutionss",
        default     = 1
    )

    types = [('point', 'point', ''), ('spot', 'spot', '')]
    lamp_type = bpy.props.EnumProperty(
        name    = "Material distribution method",
        items   = types, 
        default = 'spot',
        update  = update_type
    )

    lamp_intensity = bpy.props.FloatProperty(
        name        = "lamp_intensity",
        description = "Size (and softness of shadows) of the array's lamps",
        default     = 1.0,
        update      = update_intensity
    )

    lamp_size = bpy.props.FloatProperty(
        name        = "lamp_size",
        description = "Size (and softness of shadows) of the array's lamps",
        default     = 1.0,
        update      = update_size
    )


def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.fake_hdr_props = bpy.props.PointerProperty( 
        type = fake_HDR_props
    )
    bpy.types.Scene.fake_hdr_image = bpy.props.StringProperty()
    
def unregister():
    bpy.utils.unregister_module(__name__)
