# P3M Tools
A Blender add-on to import Perfect 3D Model (.p3m) files

----
```cpp
#define INVALID_BONE_INDEX 255 // or 0xFF

struct vector_t {
    float x;
    float y;
    float z;
}; // 12 bytes

struct position_bone_t {
    vector_t position;
    
    unsigned char children[10];
}; // 24 bytes (2-byte padding at the end of the struct)

struct angle_bone_t {
    // these two fields are represented by a 4x4 float matrix during runtime
    vector_t position;
    float scale;

    unsigned char children[10];
}; // 28 bytes (2-byte padding at the end of the struct)

struct triangle_t {
    unsigned short point[3];
}; // 6 bytes

struct vertex_t {
    vector_t position;
    float w; // bone weight (influence). It seems that it's always 1.0

    // bone weight painting. Each vertex seems to be influenced always by a single bone.
    // The index used during runtime is (byte)(index - bone_position_count) repeated 4 times, 
    // hence the hypothesis that each vertex is influenced by a single bone.
    unsigned int index; 

    vector_t normal; // used for lighting
    float tu, tv; // texture coordinates (used for texture mapping)
}; // 40 bytes

struct p3m_file {
    char version[27];

    // Bone information
    unsigned char bone_position_count;
    unsigned char bone_angle_count;

    position_bone_t bone_positions[bone_position_count];
    angle_bone_t bone_angles[bone_angle_count];

    // Mesh information
    unsigned char vertex_count;
    unsigned char face_count;

    char texture_filename[260];

    triangle_t faces[face_count];
    vertex_t vertices[vertex_count];

    // gibblerish data?
};
```

```cpp
bool GCDeviceMeshP3M::Load();
```
