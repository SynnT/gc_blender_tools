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
    "name": "FRM (.frm) Importer",
    "author": "Gabriel F. (Synn)",
    "description": "Imports .frm animation files into Blender.",
    "blender": (2, 80, 0),
    "version": (1, 0, 0),
    "location": "File > Import > FRM (.frm)",
    "warning": "",
    "category": "Import-Export"
}


import os
import struct

import bmesh
import bpy
import mathutils
from bpy.props import (CollectionProperty, StringProperty)
from bpy.types import Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper


def import_frm(context, filepath):
    model_name = bpy.path.basename(filepath)

    print("[Importing %s]" % animation_name)

    animation_name = os.path.splitext(animation_name)[0]

    file_object = open(filepath, 'rb')


    # corrects orientation
    correct_orientation = mathutils.Matrix([[-1.0, 0.0, 0.0, 0.0],
                                            [0.0, 0.0, 1.0, 0.0],
                                            [0.0, 1.0, 0.0, 0.0],
                                            [0.0, 0.0, 0.0, 1.0]])


class ImportFile(Operator, ImportHelper):
    """Import a FRM file"""
    bl_idname = "import_animation.frm"
    bl_label = "Import FRM"

    filename_ext = ".frm"

    filter_glob: StringProperty(
        default="*.frm",
        options={'HIDDEN'},
        maxlen=255,
    )

    files: CollectionProperty(
        name="FRM files",
        type=OperatorFileListElement,
    )

    directory = StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        for file in self.files:
            path = os.path.join(self.directory, file.name)
            import_frm(context, path)

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportFile.bl_idname, text="FRM (.frm)")


def register():
    bpy.utils.register_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
    bpy.ops.import_model.p3m('INVOKE_DEFAULT')
