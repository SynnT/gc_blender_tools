# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Perfect 3D Model (.p3m) Importer",
    "author": "Gabriel F. (Frihet Dev)",
    "description": "Imports .p3m files into Blender, including meshes and bones.",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "File > Import > Perfect 3D Model (.p3m)",
    "warning": "",
    "category": "Import-Export"
}


import bpy
import os
import mathutils
import struct


def import_p3m(context, filepath):
    AUTO_SIZE_SCALE = 0.0045767944 * 1.1

    model_name = bpy.path.basename(filepath)

    print("Importing", model_name)

    model_name = os.path.splitext(model_name)[0]

    file_object = open(filepath, 'rb')

    file_object.read(27) # skips the version

    data = file_object.read(2)
    bone_position_count, bone_angle_count = struct.unpack('<2B', data)

    # DEBUG
    print("bone_position_count:", bone_position_count)
    print("bone_angle_count:", bone_angle_count)

    # TEST
    armature = bpy.data.armatures.new('Armature')
    armature_object = bpy.data.objects.new('Armature_object', armature)

    bpy.context.collection.objects.link(armature_object)
    context.view_layer.objects.active = armature_object

    bpy.ops.object.mode_set(mode='EDIT')

    angle_pos_map = [None] * bone_angle_count

    for x in range(bone_position_count):
        data = file_object.read(3 * 4)
        position_x, position_y, position_z = struct.unpack('<3f', data)

        # scales the vectors back
        position_x = position_x / AUTO_SIZE_SCALE
        position_y = position_y / AUTO_SIZE_SCALE
        position_z = position_z / AUTO_SIZE_SCALE

        # DEBUG
        print("\tx: %f\ty: %f\tz: %f" % (position_x, position_y, position_z))
        
        joint = armature.edit_bones.new("position_%d" % x)
        joint.head = mathutils.Vector((0, 0, 0))
        joint.tail = mathutils.Vector((position_x, position_y, position_z))

        for _ in range(10):
            data = file_object.read(1)
            angle_index, = struct.unpack('<1B', data)

            if angle_index != 255:
                # DEBUG
                print("\t-> angle_%d" % (angle_index))

                angle_pos_map[angle_index] = x

        file_object.read(2) # ignores the padding

    for x in range(bone_angle_count):
        file_object.read(4 * 4)
        
        for _ in range(10):
            data = file_object.read(1)
            position_index, = struct.unpack('<1B', data)

            if position_index != 255:
                # DEBUG
                print("angle_%d -> position_%d" % (x, position_index))
                
                if angle_pos_map[x] != None:
                    parent = armature.edit_bones[angle_pos_map[x]]
                    child = armature.edit_bones[position_index]

                    child.parent = parent
                    child.head = parent.tail                
                    child.tail = child.tail + parent.tail

        file_object.read(2) # ignores the padding

                

    # fixes orientation
    armature.transform(mathutils.Matrix([[-1.0, 0.0, 0.0, 0.0],
                                          [0.0, 0.0, 1.0, 0.0],
                                          [0.0, 1.0, 0.0, 0.0],
                                          [0.0, 0.0, 0.0, 1.0]]))

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """Import a P3M file"""
    bl_idname = "import_model.p3m"
    bl_label = "Import P3M"

    # ImportHelper mixin class uses this
    filename_ext = ".p3m"

    filter_glob: StringProperty(
        default="*.p3m",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return import_p3m(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Perfect 3D Model (.p3m)")


def register():
    bpy.utils.register_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_model.p3m('INVOKE_DEFAULT')
