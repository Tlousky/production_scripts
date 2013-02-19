import bpy, time

prefix   = 'bone_selector_'
now_time = time.localtime( time.time())
filename = prefix + str(now_time)

for bone in bpy.context.object.data.bones:
     if bone.select == True:
        print( "bpy.context.object.data.bones['%s'].select = True" % bone.name )

