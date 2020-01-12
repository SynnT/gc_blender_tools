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
    "author": "Gabriel F. (Synn)",
    "description": "Imports .p3m files into Blender, including meshes and bones.",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "File > Import > Perfect 3D Model (.p3m)",
    "warning": "",
    "category": "Import-Export"
}


import os
import struct

import bmesh
import bpy
import mathutils
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper

correct_orientation = mathutils.Matrix([[-1.0, 0.0, 0.0, 0.0],
                                        [0.0, 0.0, 1.0, 0.0],
                                        [0.0, 1.0, 0.0, 0.0],
                                        [0.0, 0.0, 0.0, 1.0]])


def import_p3m(context, filepath):
    model_name = bpy.path.basename(filepath)

    print("Importing", model_name)

    model_name = os.path.splitext(model_name)[0]

    file_object = open(filepath, 'rb')

    file_object.read(27) # skips the version

    print("Reading bones...")

    data = file_object.read(2)
    bone_position_count, bone_angle_count = struct.unpack('<2B', data)

    # DEBUG
    print("bone_position_count:", bone_position_count)
    print("bone_angle_count:", bone_angle_count)

    armature = bpy.data.armatures.new('Armature')
    armature_object = bpy.data.objects.new("%s_armature" % model_name, armature)

    bpy.context.collection.objects.link(armature_object)
    context.view_layer.objects.active = armature_object

    bpy.ops.object.mode_set(mode='EDIT')

    bone_positions = [None] * bone_position_count
    angle_to_pos = [None] * bone_angle_count

    for x in range(bone_position_count):
        data = file_object.read(3 * 4)
        px, py, pz = struct.unpack('<3f', data)

        # DEBUG
        print("position_%d:" % x)
        print("\tx: %f\ty: %f\tz: %f" % (px, py, pz))

        children_angles = []

        for _ in range(10):
            data = file_object.read(1)
            angle_index, = struct.unpack('<1B', data)

            if angle_index != 255:
                # DEBUG
                print("\t-> angle_%d" % (angle_index))

                children_angles.append(angle_index)
                angle_to_pos[angle_index] = (px, py, pz)

        bone_positions[x] = ((px, py, pz), children_angles)

        file_object.read(2) # ignores the padding

    bone_angles = [None] * bone_angle_count 

    for x in range(bone_angle_count):
        file_object.read(4 * 4)

        joint = armature.edit_bones.new("bone_%d" % x)
        joint.head = mathutils.Vector(angle_to_pos[x])
        joint.tail = mathutils.Vector(angle_to_pos[x])

        children_positions = []
        
        for _ in range(10):
            data = file_object.read(1)
            position_index, = struct.unpack('<1B', data)

            if position_index != 255:
                # DEBUG
                print("angle_%d -> position_%d" % (x, position_index))

                children_positions.append(position_index)

        bone_angles[x] = children_positions

        file_object.read(2) # ignores the padding

    for x in range(bone_angle_count):
        children_indexes = []

        for pos in bone_angles[x]:
            for ang in bone_positions[pos][1]:
                print("angle_%d" % ang)
                children_indexes.append(ang)

        if len(children_indexes) == 0:
            current = armature.edit_bones[x]
            parent = current.parent

            v = (parent.tail - parent.head).normalized() * 0.05

            current.tail = current.head + v

        elif len(children_indexes) == 1:
            parent = armature.edit_bones[x]
            child = armature.edit_bones[children_indexes[0]]

            child.parent = parent
            child.head = parent.head + child.head
            parent.tail = child.head

        else:
            parent = armature.edit_bones[x]

            new_tail = mathutils.Vector((0, 0, 0))
            
            for idx in children_indexes:
                child = armature.edit_bones[idx]

                child.parent = parent
                child.head = parent.head + child.head

                new_tail = new_tail + child.head

            parent.tail = new_tail.normalized() * 0.05

    print("Reading mesh...")

    data = file_object.read(4)
    vertex_count, face_count = struct.unpack('<2H', data)

    # DEBUG
    print("vertex_count:", vertex_count)
    print("face_count:", face_count)

    file_object.read(260) # ignores the texture_filename

    print("Reading faces...")

    faces = []

    for x in range(face_count):
        data = file_object.read(3 * 2)
        a, b, c = struct.unpack('<3H', data)

        faces.append((a, b, c))

    print("Reading vertices...")

    bm = bmesh.new()
    mesh = bpy.data.meshes.new("%s_mesh" % model_name)

    vertices = []

    for x in range(vertex_count):
        data = file_object.read(40)
        px, py, pz, weight, index, nx, ny, nz, tu, tv = struct.unpack('<3f1f1B3x3f2f', data)

        if index != 255:
            index = index - bone_position_count
            
            px += armature.edit_bones[index].head[0]
            py += armature.edit_bones[index].head[1]
            pz += armature.edit_bones[index].head[2]

        tv = 1 - tv

        vertex = bm.verts.new((px, py, pz))

        vertex.normal = mathutils.Vector((nx, ny, nz))
        vertex.normal_update()

        vertices.append((index, weight, tu, tv))

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    
    print("Setting UV coordinates...")

    uv_layer = bm.loops.layers.uv.verify()

    for f in faces:
        a = bm.verts[f[0]]
        b = bm.verts[f[1]]
        c = bm.verts[f[2]]

        try:
            face = bm.faces.new((a, b, c))
        except:
            pass

        for vert, loop in zip(face.verts, face.loops):
            tu = vertices[vert.index][2]
            tv = vertices[vert.index][3]

            loop[uv_layer].uv = (tu, tv)

    bm.to_mesh(mesh)
    bm.free()

    mesh_object = bpy.data.objects.new("%s_mesh" % model_name, mesh)

    print("Setting vertex weights...")

    for x in range(bone_angle_count):
        mesh_object.vertex_groups.new(name="bone_%d" % x)

    for i, vertex in enumerate(vertices):
        if index != 255:
            index = vertex[0]
            weight = vertex[1]
            
            mesh_object.vertex_groups[index].add([i], weight, "REPLACE")

    # fixes orientation
    armature.transform(correct_orientation)
    mesh.transform(correct_orientation)

    bpy.ops.object.mode_set(mode='OBJECT')

    mesh_object.parent = armature_object
    modifier = mesh_object.modifiers.new(type='ARMATURE', name="Armature")
    modifier.object = armature_object

    bpy.context.collection.objects.link(mesh_object)
    context.view_layer.objects.active = mesh_object
            

    return {'FINISHED'}

class ImportFile(Operator, ImportHelper):
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
    self.layout.operator(ImportFile.bl_idname, text="Perfect 3D Model (.p3m)")


def register():
    bpy.utils.register_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_model.p3m('INVOKE_DEFAULT')
