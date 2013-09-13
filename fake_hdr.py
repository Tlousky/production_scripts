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
#  Studio (sponsor)  : PitchiPoy Animation Productions (PitchiPoy.tv)
#  Start of project  : 2013-11-08 by Tamir Lousky
#  Last modified     : 2013-13-09
#
#  Acknowledgements 
#  ================
#  PitchiPoy: Nathan Elias    (for suggesting the idea)
#             Dima Kondrashov (for feature suggestions and testing)
#  Zeffii @ StackExchange - for providing really useful insights and sample code 
#                           on how vertex colors can be matched with mesh verts.
#  Matan Harel from XLN.org.il: who helped me with the calculations related to
#                               converting from number of lamps to icosphere
#                               subdivisions.

bl_info = {    
    "name"        : "Fake HDR",
    "author"      : "Tamir Lousky",
    "version"     : (0, 0, 2),
    "blender"     : (2, 68, 0),
    "category"    : "Render",
    "location"    : "3D View >> Tools",
    "wiki_url"    : "https://github.com/Tlousky/production_scripts/wiki/Fake-HDR",
    "tracker_url" : "https://github.com/Tlousky/production_scripts/blob/master/fake_hdr.py",
    "description" : "Create an array of lamps that mimicks an HDR image"
}

import bpy, re, bmesh, math
from collections import defaultdict
from mathutils   import Color

def check_poll_conditions( context ):
    hdr_image_selected  = context.scene.fake_hdr_image
    render_engine_is_bi = context.scene.render.engine == 'BLENDER_RENDER'
    return hdr_image_selected and render_engine_is_bi

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

        col.prop( props, 'num_of_lamps' )

        layout.operator( 'render.create_hdr_sphere' )

        if 'FakeHDR.LightArray.Control' in context.scene.objects:
            lbl = layout.label( "Update lamp properties" )
            box = layout.box()
            col = box.column()

            col.prop( context.scene.fake_hdr_props, 'lamp_type'         )
            col.prop( context.scene.fake_hdr_props, 'lamp_intensity'    )
            col.prop( context.scene.fake_hdr_props, 'lamp_distance'     )
            col.prop( context.scene.fake_hdr_props, 'lamp_shadow_type'  )
            col.prop( context.scene.fake_hdr_props, 'lamp_use_specular' )
            
            if props.lamp_shadow_type == 'RAY_SHADOW':
                col.prop( context.scene.fake_hdr_props, 'lamp_ray_samples' )

            col.prop( context.scene.fake_hdr_props, 'lamp_size' )

            lbl = layout.label( "Make sun lamp of strongest light" )
            box = layout.box()
            col = box.column()
            
            col.prop( context.scene.fake_hdr_props, 'use_sun' )
            if context.scene.fake_hdr_props.use_sun:
                col.prop( context.scene.fake_hdr_props, 'sun_intensity' )
        
class create_hdr_sphere( bpy.types.Operator ):
    """ Create a file output node for each pass in each renderlayer """
    bl_idname      = "render.create_hdr_sphere"
    bl_label       = "Create light array"
    bl_description = "Create a light array corresponding to an HDR sphere"
    bl_options     = {'REGISTER', 'UNDO' }

    @classmethod
    def poll( self, context ):
        return check_poll_conditions( context )

    def create_sphere( self, context, n ):
        bm = bmesh.new()
        
        # Calculate sphere subdivisions
        subd = math.trunc( math.log( n / 2.6 ) / 1.37 ) + 1

        # Create new icosphere mesh
        sphere_verts = bmesh.ops.create_icosphere( 
            bm, 
            subdivisions = subd,
            diameter     = 1
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
        context.scene.render.use_bake_to_vertex_color = True
        context.scene.render.bake_type                = 'TEXTURE'

        # Add vertex color map
        bpy.ops.mesh.vertex_color_add()

        # Bake
        bpy.ops.object.bake_image()
        
        # Make sphere unrendereable
        obj.hide_render = True

    def sort_by_value( self, colors, sorted_list, calls ):
        """ Recursive sorting algorithm meant to find the smallest to highest
            color values in a list of averaged vertex colors """
            
        # Find the indices that have not been sorted yet
        unsorted_indices = set( colors.keys() ).difference( set( sorted_list ) )
        
        min        = 4.0
        smallest_i = 0
        # Find current darkest vertex
        for i in unsorted_indices:
            val = sum( [ c for c in colors[i][:] ] )
            if val < min:
                smallest_i = i
                min        = val

        # Add it to the list of sorted verts
        sorted_list.append( smallest_i )

        # If we sorted all the verts, we can return them and exit the function. 
        # Otherwiese, call it again with the new (incomplete) sorted vert list.
        if len( sorted_list ) == len( colors ):
            return sorted_list
        else:
            return self.sort_by_value( colors, sorted_list, calls + 1 )
            
    def get_vcolors( self, context, obj, n ):
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
                sum( [ c.b for c in vcolor_dict[v] ] ) / len( vcolor_dict[v] )
            ) )

        # Sort verts by value
        verts_sorted_by_value = self.sort_by_value( avg_vcolors, [], 1 )

        start = len( avg_vcolors ) - n
        culled_vert_list = verts_sorted_by_value[ start: ]
        
        vcolors = { v : avg_vcolors[v] for v in culled_vert_list }
        
        return vcolors
        
    def create_lamps( self, context, obj ):
        # Create empty which will act as the lamps' parent object
        bpy.ops.object.empty_add( type = 'SPHERE' )

        empty      = context.scene.objects[ context.object.name ]
        empty.name = 'FakeHDR.LightArray.Control' 

        # Set empty as the sphere's parent
        obj.parent = empty

        n       = context.scene.fake_hdr_props.num_of_lamps
        lamps   = []
        verts   = obj.data.vertices
        vcolors = self.get_vcolors( context, obj, n )
        
        for i,v in enumerate( vcolors.keys() ):
            bpy.ops.object.lamp_add( type = 'POINT' )

            # Reference lamp (which is now the selected and active object
            lamp      = context.scene.objects[ context.object.name ]
            lamp.name = 'fake_hdr_lamp'
            lamps.append( lamp.name )

            # Parent lamp to empty, and:
            # Create damped track constraint from lamp to empty to make sure
            # spots and sun always look in the direction of the empty
            lamp.parent      = empty 
            const            = lamp.constraints.new( type = 'DAMPED_TRACK' )
            const.target     = empty
            const.track_axis = 'TRACK_NEGATIVE_Z'

            # Set lamp location
            lamp.location = verts[v].co
            
            # Set lamp color
            lamp.data.color = vcolors[v]
            
            # Set all default parameters
            props = context.scene.fake_hdr_props
            lamp.data.distance           = props.lamp_distance
            lamp.data.shadow_ray_samples = props.lamp_ray_samples
            lamp.data.shadow_soft_size   = props.lamp_size
            lamp.data.use_specular       = props.lamp_use_specular
            
            # make the strongest lamp a sun if option is turned on
            if context.scene.fake_hdr_props.use_sun and i == len( vcolors ) - 1:
                lamp.data.type = 'SUN'
                value = context.scene.fake_hdr_props.sun_intensity
                change_light_intensity( lamp, value )

        return lamps

    def execute( self, context ):
        n   = context.scene.fake_hdr_props.num_of_lamps
        obj = self.create_sphere( context, n )
        self.map_hdr_to_sphere( context, obj )
        self.bake_textures_to_verts( context, obj )
        lamps = self.create_lamps( context, obj )
        
        return {'FINISHED'}

class fake_HDR_props( bpy.types.PropertyGroup ):
    def find_lamps( self, context ):
        empty = context.scene.objects['FakeHDR.LightArray.Control']
        return [ c for c in empty.children if c.type == 'LAMP' ]   

    def update_intensity( self, context ):
        value  = context.scene.fake_hdr_props.lamp_intensity
        svalue = context.scene.fake_hdr_props.sun_intensity
        for l in self.find_lamps(context):
            if l.data.type != 'SUN':
                change_light_intensity( l, value )
            else:
                change_light_intensity( l, svalue )

    def update_size( self, context ):
        for l in self.find_lamps(context):
            l.data.shadow_soft_size = context.scene.fake_hdr_props.lamp_size

    def update_type( self, context ):
        for l in self.find_lamps(context):
            if l.data.type != 'SUN':
                l.data.type = context.scene.fake_hdr_props.lamp_type

    def update_distance( self, context ):
        for l in self.find_lamps(context):
            l.data.distance = context.scene.fake_hdr_props.lamp_distance

    def update_use_specular( self, context ):
        for l in self.find_lamps(context):
            l.data.use_specular = context.scene.fake_hdr_props.lamp_use_specular

    def update_shadow_type( self, context ):
        value = context.scene.fake_hdr_props.lamp_shadow_type
        for l in self.find_lamps(context):
            l.data.shadow_method = value

    def update_ray_samples( self, context ):
        value = context.scene.fake_hdr_props.lamp_ray_samples
        for l in self.find_lamps(context):
            l.data.shadow_ray_samples = value

    def update_use_sun( self, context ):
        lamps      = self.find_lamps(context)
        sun_exists = 'SUN' in [ l.data.type for l in lamps ]
        use_sun    = context.scene.fake_hdr_props.use_sun

        if not use_sun:
            if sun_exists:
                default_type = context.scene.fake_hdr_props.lamp_type
                default_int  = context.scene.fake_hdr_props.lamp_intensity

                for l in lamps:
                    if l.data.type == 'SUN':
                        l.data.type = default_type
                        change_light_intensity( l, default_int )

        else:
            intensities = {          # Summarize rgb to get intensity
                l : sum( [ c for c in l.data.color ] ) for l in lamps
            }
        
            max_lightint = max( intensities.values() ) # Find highest intensity

            for l,i in intensities.items():
                if i == max_lightint:
                    l.data.type = 'SUN'

                    value = context.scene.fake_hdr_props.sun_intensity
                    change_light_intensity( l, value )

                    break # Make sure than no more than one sun exists

    num_of_lamps = bpy.props.IntProperty(
        description = "Number of Lamps in scene",
        name        = "Number of Lamps",
        default     = 50,
        min         = 12,
        max         = 2500
    )
                    
    types = [('POINT', 'point', ''), ('SPOT', 'spot', '')]
    lamp_type = bpy.props.EnumProperty(
        name    = "Lamp Type",
        items   = types, 
        default = 'SPOT',
        update  = update_type
    )

    lamp_intensity = bpy.props.FloatProperty(
        name        = "Lamp light intensity",
        description = "Size (and softness of shadows) of the array's lamps",
        default     = 1.0,
        update      = update_intensity
    )

    lamp_size = bpy.props.FloatProperty(
        name        = "Lamp shadow size",
        description = "Size (and softness of shadows) of the array's lamps",
        default     = 1.0,
        update      = update_size
    )

    lamp_distance = bpy.props.FloatProperty(
        name        = "Lamp distance",
        description = "Distance (affects intensity due to falloff)",
        default     = 25.0,
        update      = update_distance
    )

    lamp_use_specular = bpy.props.BoolProperty(
        name        = "Use specular",
        description = "If true - lamps create specular highlights",
        default     = True,
        update      = update_use_specular
    )

    shadow_types = [('NOSHADOW', 'No Shadow', ''), ('RAY_SHADOW', 'Ray Shadow', '')]
    lamp_shadow_type = bpy.props.EnumProperty(
        name    = "Shadow type",
        items   = shadow_types, 
        default = 'NOSHADOW',
        update  = update_shadow_type
    )

    lamp_ray_samples = bpy.props.IntProperty(
        name        = "Ray shadow samples",
        description = "Number of ray shadow samples (i.e. quality)",
        default     = 5,
        update      = update_ray_samples
    )

    use_sun = bpy.props.BoolProperty(
        name        = "Create sun",
        description = "Make strongest light a sun lamp",
        default     = True,
        update      = update_use_sun
    )

    sun_intensity = bpy.props.FloatProperty(
        name        = "Sun intensity",
        description = "The intensity of the sun lamp",
        default     = 5.0,
        update      = update_intensity
    )

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.fake_hdr_props = bpy.props.PointerProperty( 
        type = fake_HDR_props
    )
    bpy.types.Scene.fake_hdr_image = bpy.props.StringProperty()
    
def unregister():
    bpy.utils.unregister_module(__name__)
