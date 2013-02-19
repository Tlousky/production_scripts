import bpy, time

prefix   = 'bone_selector_'             # Textfile prefix
now_time = time.localtime( time.time()) # Current time
filename = prefix + str(now_time)       # Concatenate prefix and time to create unique name

# Create a new text file in the text editor
bpy.data.texts.new(name=filename)
textfile = bpy.data.texts[filename]

start_string = """ import bpy

"""

# List all existing bone names
bone_names     = [ name for bone.name in bpy.context.object.data.bones ]
selected_bones = [ name for bone.name in bpy.context.object.data.bones if bone.select == True ]

for name in bone_names:
   if name in selected_bones:
      textfile.write("bpy.context.object.data.bones['%s'].select = True" % bone.name  + "\n")
   else:
      textfile.write("bpy.context.object.data.bones['%s'].select = False" % bone.name  + "\n")
