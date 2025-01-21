import bpy, time
from bpy.utils import register_class, unregister_class

# bl_info = {
#     "name" : "Clear Filepaths",
#     "location" : "Top toolbar > File > Clean Up > Clear Blender Filepaths",
#     "description" : 'Removes personal filepaths from your blender file',
#     "blender" : (3, 6, 2),
#     "category" : "System",
# }

class cbf(bpy.types.Operator):
    bl_label = "Clear Filepaths and Close Blender"
    bl_idname = "cbf.cleanfilepaths"
    bl_description = '''Save an uncompressed copy of the current file with personal filepaths cleared like
"C:\\Users\\my username\\Embarassing folder name\\", and
"D:\\Personal stuff\\Oh my gosh I can\'t believe this was saved to that blend file I put on Gumroad\\"
The new file will be saved with the current filename + "_cleaned" at the end. Blender will close once the cleaned file is saved to prevent it from being overwritten. A text file with the cleared filepaths will also be saved'''

    def execute(self, context):
        #don't run this if the file has not been saved yet (filepath will be blank if that's the case)
        if bpy.data.filepath:        
            self.save_new_file()
            self.find_and_overwrite_filepaths()
            self.close_blender()
        return {'FINISHED'}

    def save_new_file(self):
        '''save the file as an uncompressed file next to the original'''
        bpy.ops.wm.save_as_mainfile(filepath = bpy.data.filepath.replace('.blend', '_cleaned.blend'), compress = False, relative_remap = False)

    def find_and_overwrite_filepaths(self):
        '''collects all accessible filepaths and removes them from the new file. also creates copies of everything and remaps them to remove non-accessible filepaths'''
        #collect all filepaths
        filepath_list = []
        def add(this):
            if this and (this not in filepath_list):
                filepath_list.append(this)

        categories = bpy.data.__dir__()
        remove_these = ['bl_rna', 'use_autopack', 'is_saved', 'is_dirty', 'rna_type', '__doc__', 'filepath', 'version', 'scenes', 'screens', 'window_managers', 'workspaces', 'fonts']
        for remove in remove_these:
            categories.remove(remove)
        
        #get a list of hidden objects and hidden collections, so if they need to be duplicated later, they can retain their hide state
        hide = []
        hide_viewport = []
        hide_render = []
        def recursive_find_hidden_child(layer_col):
            if layer_col:
                if layer_col.exclude:
                    hide.append(layer_col.name)
                if layer_col.hide_viewport:
                    hide_viewport.append(layer_col.name)
                if len(layer_col.children):
                    for child in layer_col.children:
                        recursive_find_hidden_child(child)

        def recursive_write_hidden_child(layer_col):
            if layer_col:
                if layer_col.name in hide:
                    layer_col.exclude = True
                if layer_col.name in hide_viewport:
                    layer_col.hide_viewport = True
                if layer_col.name in hide_render:
                    bpy.data.collections[layer_col.name].hide_render = True
                if len(layer_col.children):
                    for child in layer_col.children:
                        recursive_write_hidden_child(child)

        for c in bpy.data.collections:
            if c.hide_render:
                hide_render.append(c.name)
            layer_col = bpy.context.view_layer.layer_collection.children.get(c.name)
            recursive_find_hidden_child(layer_col)
        for o in bpy.data.objects:
            if o.hide_get():
                hide.append(o.name)
            if o.hide_render:
                hide_render.append(o.name)
            if o.hide_viewport:
                hide_viewport.append(o.name)
        
        #Now go through every category and item, and look for filepath instances
        #If one is found, add it to the filepath_list array
        for category in categories:
            # print(category)
            cat = getattr(bpy.data, category)
            if not callable(cat):
                for item in cat:
                    # print(item)
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
                    #some things still have a filepath property that I cannot find through the python api
                    #Make a copy of anything with the name attribute, then remap every instance with the copy
                    #The copy will no longer have the mysterious filepath property
                    if getattr(item, 'name', None):
                        original_name = item.name
                        copy = item.copy()
                        item.user_remap(copy)
                        item.name = 'old delete'
                        copy.name = original_name
                        try:
                            cat.remove(item)
                        except:
                            #This was likely a shapekey, and shapekeys don't have a remove function. Just use the orphan purge func to clear the old one instead
                            bpy.ops.outliner.orphans_purge() 
                        #preserve hide / exclude state before the item was copied
                        if category == 'collections':
                            layer_col = bpy.context.view_layer.layer_collection.children.get(copy.name)
                            recursive_write_hidden_child(layer_col)
                        elif category == 'objects' and copy.name in hide:
                            copy.hide_set(True)
                        if category == 'objects' and copy.name in hide_render:
                            copy.hide_render = True
                        if category == 'objects' and copy.name in hide_viewport:
                            copy.hide_viewport = True
        
        #add these filepaths too if they were missed
        add(bpy.data.filepath)
        add(bpy.context.scene.render.filepath if bpy.context.scene.render.filepath != '/tmp\\' else None)

        #save one more time after doing the copy remap
        bpy.ops.wm.save_mainfile(compress = False, relative_remap = False)

        #read the whole file in and check for any filepath instances
        original_filepath = bpy.data.filepath
        file = open(original_filepath, 'rb')
        raw_data = file.read()
        for path in filepath_list:
            raw_data = raw_data.replace(path.encode(), b'b'*len(path))
        
        file.close()
        #overwrite the file with filepaths replaced as 'bbbbbbb'
        with open(original_filepath, 'wb') as file:
            file.write(raw_data)
            time.sleep(1)
        
        #also add a text file that lists out the removed filepaths
        with open(original_filepath.replace('.blend', '_info.txt'), 'w') as file:
            file.write(str(filepath_list).replace(',',',\n'))

    def close_blender(self):
        '''close blender so the cleaned file is not accidentally overwritten'''
        bpy.ops.wm.quit_blender()
        return {'FINISHED'}

def menu_draw(self, context):
        self.layout.operator("cbf.cleanfilepaths")

def wrap(register_bool):
    register_class(cbf) if register_bool else unregister_class(cbf)
    bpy.types.TOPBAR_MT_file_cleanup.append(menu_draw) if register_bool else bpy.types.TOPBAR_MT_file_cleanup.remove(menu_draw)

def register():
    wrap(True)

def unregister():
    wrap(False)

if __name__ == "__main__":
    register()
