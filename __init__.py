import bpy
from bpy.utils import register_class, unregister_class

bl_info = {
    "name" : "Clear Blender Filepaths",
    "location" : "Top toolbar > File > Clean Up > Clear Blender Filepaths",
    "description" : 'Removes personal filepaths from your blender file',
    "blender" : (3, 6, 2),
    "category" : "System",
}

class cbf(bpy.types.Operator):
    bl_label = "Clear Filepaths"
    bl_idname = "cbf.cleanblenderfilepaths"
    bl_description = '''Save an uncompressed copy of your .blend file with personal filepaths cleared like
"C:\\Users\\my username\\Embarassing folder name\\", and
"D:\\Personal stuff\\Oh my god I can\'t believe this was saved to that blend file I put on Gumroad\\"'''

    def execute(self, context):

        #don't run if the file has not been saved yet
        if not bpy.data.filepath:
            return {'FINISHED'}
        
        #save the file as an uncompressed file next to the original
        bpy.ops.wm.save_as_mainfile(filepath = bpy.data.filepath.replace('.blend', '_cleaned.blend'), compress = False, relative_remap = False)

        #collect all filepaths
        filepath_list = []
        def add(this):
            if this and (this not in filepath_list):
                filepath_list.append(this)
        
        for cat in [bpy.data.images,
                    bpy.data.objects,
                    bpy.data.linestyles,
                    bpy.data.materials,
                    bpy.data.node_groups,
                    bpy.data.texts,
                    bpy.data.cameras,
                    bpy.data.lights,
                    bpy.data.meshes]:
            for item in cat:
                for check in ['filepath', 'filepath_raw']:
                    if getattr(item, check, None):
                        add(getattr(item, check, None))
                    if getattr(item, 'original', None):
                        if getattr(item.original, 'filepath', None):
                            add(item.original.filepath)
                    if getattr(item, 'library_weak_reference', None):
                        if getattr(item.library_weak_reference, 'filepath', None):
                            add(item.library_weak_reference.filepath)
                    if getattr(item, 'packed_files', None):
                        for packed_file in getattr(item, 'packed_files', []):
                            if getattr(packed_file, 'filepath', None):
                                add(packed_file.filepath)     
                                    
        add(bpy.data.filepath)
        add(bpy.context.scene.render.filepath if bpy.context.scene.render.filepath != '/tmp\\' else None)

        #read the whole file in and check for any filepath instances
        original_filepath = bpy.data.filepath
        file = open(original_filepath, 'rb')
        raw_data = file.read()
        for path in filepath_list:
            raw_data = raw_data.replace(path.encode(), b'b'*len(path))
        
        file.close()
        #overwrite the file with filepaths replaced as 'bbbbbbb'
        file = open(original_filepath, 'wb')
        file.write(raw_data)
        file.close()

        #close blender so the cleaned file is not accidentally overwritten
        bpy.ops.wm.quit_blender()
        return {'FINISHED'}

def menu_draw(self, context):
        self.layout.operator("cbf.cleanblenderfilepaths")

def wrap(register_bool):
    register_class(cbf) if register_bool else unregister_class(cbf)
    bpy.types.TOPBAR_MT_file_cleanup.append(menu_draw) if register_bool else bpy.types.TOPBAR_MT_file_cleanup.remove(menu_draw)

def register():
    wrap(True)

def unregister():
    wrap(False)

if __name__ == "__main__":
    register()
