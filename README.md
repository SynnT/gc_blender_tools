# P3M Tools
A Blender add-on to import Perfect 3D Model (.p3m) files

----
```c
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

```
bool GCDeviceMeshP3M::Load()
{
    GCMemoryFile memfile(g_pGCDeviceManager->GetMassFileManager(), m_strFileName);

    if (!memfile.IsLoaded())
    {
        m_eDeviceState = GCDS_DISABLE;
        return false;
    }

    char strVersion[27];
    memfile.ReadFile(strVersion, sizeof(char) * 27);

    BYTE NumPositionBone;
    memfile.ReadFile(&(NumPositionBone), sizeof(BYTE));
    m_dwNumPositionBone = NumPositionBone;

    BYTE NumAngleBone;
    memfile.ReadFile(&(NumAngleBone), sizeof(BYTE));
    m_dwNumAngleBone = NumAngleBone;

    KAngleBoneFromFile *pTempABone = new KAngleBoneFromFile[m_dwNumAngleBone];

    KPositionBone *pPositionBone = new KPositionBone[m_dwNumPositionBone];
    KAngleBoneOnMemory *pAngleBone = new KAngleBoneOnMemory[m_dwNumAngleBone];

    memfile.ReadFile(pPositionBone, sizeof(KPositionBone) * m_dwNumPositionBone);
    memfile.ReadFile(pTempABone, sizeof(KAngleBoneFromFile) * m_dwNumAngleBone);

    for (DWORD l = 0; l < m_dwNumAngleBone; l++)
    {
        for (int i = 0; i < (int)pAngleBone[l].acChildIndex.size(); ++i)
        {
            pAngleBone[l].acChildIndex[i] = pTempABone[l].acChildIndex[i];
        }
    }

    SetAngleBon(pAngleBone, m_dwNumAngleBone);
    SetPositionBone(pPositionBone, m_dwNumPositionBone);

    SAFE_DELETE_ARRAY(pTempABone);

    WORD wTemp;
    memfile.ReadFile(&wTemp, sizeof(WORD));
    m_dwNumVertex = wTemp;
    memfile.ReadFile(&wTemp, sizeof(WORD));
    m_dwNumFace = wTemp;

    char strTextureFileName[260];
    memfile.ReadFile(strTextureFileName, sizeof(char) * 260);

    std::vector<ONE_TRIANGLE> vecIndex;
    vecIndex.reserve(m_dwNumFace);
    for (DWORD i = 0; i < m_dwNumFace; ++i)
    {
        ONE_TRIANGLE triangle;
        memfile.ReadFile(&triangle, sizeof(ONE_TRIANGLE));
        vecIndex.push_back(triangle);
    }
    WORD *ix;

    std::set<DWORD> setIgIdx;
    std::vector<SKINVERTEX> vecVertex;
    SKINVERTEX_SOURCE *v2 = (SKINVERTEX_SOURCE *)memfile.GetDataPointer();
    for (DWORD i = 0; i < m_dwNumVertex; ++i)
    {
        BYTE idx = (BYTE)(v2[i].index - m_dwNumPositionBone);
        if (m_cIgBoneIdx != -1 && (idx == (BYTE)m_cIgBoneIdx || idx == (BYTE)m_cIgBoneIdx + 1)) // 최후의 하드코딩..
        {
            setIgIdx.insert(i);
        }

        SKINVERTEX v;
        v.Pos = v2[i].Pos;
        v.w[0] = 1.0f;
        v.indexByte[0] = v.indexByte[1] = v.indexByte[2] = v.indexByte[3] = idx;
        v.Nor = v2[i].Nor;
        v.tu = v2[i].tu;
        v.tv = v2[i].tv;

        vecVertex.push_back(v);
    }
    
    vecIndex.erase(std::remove_if(vecIndex.begin(), vecIndex.end(), RemoveFunctor(setIgIdx)), vecIndex.end());
    m_dwNumFace = (DWORD)vecIndex.size();

    SAFE_RELEASE(m_pIndexBuffer);
    if (D3D_OK != m_pd3dDevice->CreateIndexBuffer(sizeof(ONE_TRIANGLE) * m_dwNumFace, D3DUSAGE_WRITEONLY, D3DFMT_INDEX16, D3DPOOL_MANAGED, &m_pIndexBuffer, NULL))
        goto Failed;
    m_pIndexBuffer->Lock(0, 0, (void **)&ix, 0);
    memcpy(ix, &(*vecIndex.begin()), sizeof(ONE_TRIANGLE) * m_dwNumFace);
    m_pIndexBuffer->Unlock();

    SKINVERTEX *v1;
    SAFE_RELEASE(m_pVertexBuffer);
    if (D3D_OK != m_pd3dDevice->CreateVertexBuffer(m_dwNumVertex * sizeof(SKINVERTEX), D3DUSAGE_WRITEONLY, SKINVERTEX::FVF, D3DPOOL_MANAGED, &m_pVertexBuffer, NULL))
        goto Failed;
    m_pVertexBuffer->Lock(0, 0, (void **)&v1, 0);
    memcpy(v1, &(*vecVertex.begin()), m_dwNumVertex * sizeof(SKINVERTEX));
    m_pVertexBuffer->Unlock();

    m_eDeviceState = GCDS_LOADED;
    return true;

Failed:
    m_eDeviceState = GCDS_DISABLE;
    return false;
}
```
