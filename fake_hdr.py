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

# Fake HDR

# User:
# 0.  Choose an HDR image file
# Script:
# 1. Create a polysphere
# 2. UV unwrap with spherical projection
# 3. Create shadeless material
# 4. Bake texture to vertex color
# 5. Create a hair particle system with a particle per vert
# 6. Use lamp instances for particles, then make them real and single users
# 7. Iterate over vertex colors, map each to the corresponding lamp
# 8. Delete the original sphere
# 9. Parent all lamps to a spherical empty for easy transformation and scaling
# That's it!

bl_info = {    
    "name"       : "Fake HDR",
    "author"     : "Tamir Lousky",
    "version"    : (0, 0, 1),
    "blender"    : (2, 68, 0),
    "category"   : "Render",
    "location"   : "3D View >> Tools",
    "wiki_url"   : "",
    "tracker_url": "",
    "description": "Create an array of stops that mimicks an HDR image"
}

import bpy, re, bmesh

def check_poll_conditions( context ):
    hdr_image_selected = context.scene.fake_hdr_image
    rend_engine_is_bi  = context.scene.render.engine == 'BLENDER_RENDER'
    return hdr_image_selected and rend_engine_is_bi

class fake_hdr(bpy.types.Panel):
    bl_idname      = "FakeHDR"
    bl_label       = "Fake HDR"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context     = 'objectmode'

    @classmethod
    def poll( self, context ):
        return context.scene.render.engine == 'BLENDER_RENDER'

    def draw( self, context) :
        hdr_image = context.scene.fake_hdr_image
        props     = context.scene.fake_hdr_props

        layout = self.layout
        col    = layout.col

        col.prop_search(          
            context.scene, "fake_hdr_image",  # Pick HDR image 
            bpy.data, "images"                # From list of images in scene
        )

        col.prop( props, 'sphere_resolution' )

        layout.operator( 'render.create_hdr_sphere' )


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
        sphere_verts = bmesh.ops.create_icosphere( bm, subdivisions = subd )

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
        obj.mode = 'EDIT'

        # Create spherical UV map
        bpy.ops.uv.sphere_project()

        # Return to object mode
        obj.mode = 'OBJECT'

        # Add material slot to object
        bpy.ops.object.material_slot_add()

        # Create a new material and set it up
        bpy.ops.material.new()
        mat               = bpy.data.materials[-1]
        mat.name          = 'FakeHDR.Material'
        mat.use_shadeless = True

        # Set material as active on object
        C.object.material_slots[0].material = mat
        
        # Create a new texture and set it up
        bpy.data.textures.new( name = 'FakeHDR.Texture', type = 'IMAGE' )
        tex       = bpy.data.textures[-1]
        tex.image = context.scene.fake_hdr_image

        # Add material texture slot and set it up
        mat.texture_slots.add()
        mat.texture_slots[0].name           = 'FakeHDR'
        mat.texture_slots[0].texture.coords = 'UV'      # Map texture to UVs
        mat.texture_slots[0].texture        = tex

    def bake_textures_to_verts( self, context, obj ):
        # Select and make active
        context.scene.objects.active = obj
        obj.select = True

        # Set up bake textures to vert colors
        if not context.scene.render.use_bake_to_vertex_color:
            context.scene.render.use_bake_to_vertex_color = True
        if not scene.render.bake_type == 'TEXTURE':
            scene.render.bake_type = 'TEXTURE'

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
        lampobj.select = True
        bpy.ops.object.delete()

        # Reference all lamps
        lamps = [ o for o in bpy.context.scene.objects if lampname in o.name ]

        # Create empty which will act as the lamps' parent object
        bpy.ops.object.empty_add( type = 'SPHERE' )
        empty = bpy.context.scene.objects[ bpy.context.object.name ]

        # Deselect all objects
        bpy.ops.object.select_all( action = 'DESELECT' )

        # Select all lamps and parent all to empty
        for lamp in lamps:
            lamp.select = True
            lamp.parent = empty

        # Make all lamp instances single users (to enable separate control
        # over their properties)
        bpy.ops.object.make_single_user(
            type   = 'SELECTED_OBJECTS', 
            object = True, 
            obdata = True
        )
        
        return lamps

    def color_lamps( self, context, obj, lamps ):
        vcolor_points = obj.data.vertex_colors[0].data
        for c,l in zip( [ v.color for v in vcolor_points ], lamps ):
            l.data.color = c

    def execute( self, context ):
        subd = context.scene.fake_hdr_props.sphere_resolution
        obj  = self.create_sphere( context, subd )
        self.map_hdr_to_sphere( context, obj )
        self.bake_textures_to_verts( context, obj )
        lamps = self.create_lamps( context, obj )
        self.color_lamps( context, obj, lamps )


class fake_HDR_props( bpy.types.PropertyGroup ):
    sphere_resolution = bpy.props.IntProperty(
        description = "Light sphere subdivisions",
        name        = "Sphere Resolutionss",
        default     = 1
    )

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.fake_hdr_props = bpy.props.PointerProperty( 
        type = 'fake_HDR_props'
    )
    
def unregister():
    bpy.utils.unregister_module(__name__)