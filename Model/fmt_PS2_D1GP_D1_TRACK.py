'''
Hello guys!
Regarding the script update for Mortal Kombat PS2 to add weights support , stage and konquest support, please move here:
https://github.com/leeao/MortalKombat
fmt_RenderWare_PS2_PC.py current script has removed support for MK.
'''

# RenderWare DFF Models and TXD Textures Noesis Importer
# RenderWare Version 3.7.0.2 (0x1C020065)
# By Allen(Leeao)
'''
Support games:
    Manhunt [PC]
    Agent Hugo [PC]
    Silent Hill Origins [PS2]
    Shijyou Saikyou no Deshi Kenichi - Gekitou! Ragnarok Hachikengou [PS2]
    Rurouni Kenshin [PS2]
    For some RW3.7 PC / PS2 games, you can try your luck ^_^.
'''                
''' 
# 2026-04-07

PS2 D1GP .D1 TRACK MODEL FILE 
fork by raghid0401
edited script to read world sections that consist of plane sections and atomic sections and bin mesh PLG.
for now the script only reads world sections at the root of the dff. it should skip clumps just fine.
also removed anything related to reading textures because you can just rip the textures from maps with magicTXD if you rename the .d1 file to a .txd lol.



PLEASE STRIP TXD FIRST.
YOU CAN ALSO OPEN THE FILE IN RWANALYZE AND DELETE THE FIRST TXD SECTION BUT ONLY DO THIS IF OTHER SECTIONS CAN BE SEEN.

 IF YOU CAN ONLY SEE 1 TXD SECTION IN RW ANALYZE YOU WILL NEED TO USE A HEX EDITOR TO DELETE THAT FIRST TXD SECTION.
 
     USE A HEX EDITOR AND SET YOUR OFFSET TO THE SECOND 32 BIT INTEGER RIGHT AFTER THE FILE STARTS.
      THEN SCROLL A LITTLE BIT FORWARD UNTIL YOU SEE 10 00 00 00. THATS WHERE YOU WANT THE NEW FILE TO START.
       SELECT EVERYTHING BEFORE IT AND DELETE AND SAVE AS NEW. THIS NEW FILE SHOULD BE OPENABLE IN NOESIS WITH THE SCRIPT. 
         AND ALSO NOW YOU WILL SEE ALL SECTIONS IF RWANALYZE ONLY SHOWED THE TXD.


'''


from inc_noesis import *
import struct




def registerNoesisTypes():
    handle = noesis.register("PS2 D1GP .D1 TRACK MODEL", ".d1")
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadModel(handle, dffLoadModel)
    
    return 1
def noepyCheckType(data):
    bs = NoeBitStream(data)
    idstring = bs.readUInt()
    if idstring not in (0x0B,0x10,0x24):
            return 0
    return 1

def dffLoadModel(data, mdlList):
    noesis.logPopup()
    bs = NoeBitStream(data)
    
    # ONE global RPG context
    ctx = rapi.rpgCreateContext()
    
    fileSize = len(data)
    
    while bs.tell() < fileSize:
        chunk = rwChunk(bs)
        
        # skip clump for now
        #if chunk.chunkID == 0x10: #clump
        #    datas = bs.readBytes(chunk.chunkSize)
        #    clump = rClump(datas)
        #    clump.readClump()
        
        if chunk.chunkID == 0x0B: # world
            datas = bs.readBytes(chunk.chunkSize)
            world = rWorld(datas)
            world.readWorld()   # commits geometry into the SAME context
        
        
        else:
            bs.seek(chunk.chunkSize, 1)
    
    # Build ONE final model
    rapi.rpgOptimize()

    mdl = rapi.rpgConstructModel()
    mdlList.append(mdl)
    return 1




class rWorld(object):
    
    atomicIndex = 0
    def __init__(self, datas):
        self.bs = NoeBitStream(datas)
        self.atomicIndex = 0

    def readWorld(self):
        #rapi.rpgReset()

        worldSize = len(self.bs.getBuffer())
        matList = []
        print("CURRENT WORLD SIZEEEEEEEE:  ", worldSize)
        
        self.readSingleWorld(worldSize, matList)

        #return rapi.rpgConstructModel()
        return


    def readSingleWorld(self, worldSize, matList):
        worldStart = self.bs.tell()
    
        # World Struct
        worldStruct = rwChunk(self.bs)
        self.bs.seek(worldStruct.chunkSize, 1)
    
        # materialList
        nextChunkPos = self.bs.tell()
        peek = rwChunk(self.bs)
        if peek.chunkID == 0x08:
            matListData = self.bs.readBytes(peek.chunkSize)
            matListObj = rMaterialList(matListData)
            matListObj.getMaterial()
            matList = matListObj.matList
        else:
            self.bs.seek(nextChunkPos, NOESEEK_ABS)
    
        # go though child sections of the world
        while (self.bs.tell() - worldStart) < worldSize:
            sub = rwChunk(self.bs)
    
            if sub.chunkID == 0x0A: # plane section 
                self.readPlaneSection(sub.chunkSize, matList, depth=0)
            elif sub.chunkID == 0x09: # atomic section 
                self.readAtomicSection(sub.chunkSize, matList, depth=0)
            else: # idk
                self.bs.seek(sub.chunkSize, 1)
    



    def readPlaneSection(self, sectionSize, matList, depth):
         startPos = self.bs.tell()
 
         # Plane Section Struct
         structChunk = rwChunk(self.bs)  # [0x01]
         self.bs.seek(structChunk.chunkSize, 1)
 
         # Walk children inside this Plane Section
         while (self.bs.tell() - startPos) < sectionSize:
             if self.bs.tell() >= len(self.bs.getBuffer()):
                 break
 
             subChunk = rwChunk(self.bs)
 
             if subChunk.chunkID == 0x0A:  # nested Plane Section
                 self.readPlaneSection(subChunk.chunkSize, matList, depth + 1)
 
             elif subChunk.chunkID == 0x09:  # Atomic Section (leaf)
                 self.readAtomicSection(subChunk.chunkSize, matList, depth + 1)
 
             else:
                 self.bs.seek(subChunk.chunkSize, 1)
 
    def readAtomicSection(self, sectionSize, matList, depth):
    
        atomicIndex = self.atomicIndex
        self.atomicIndex += 1
    
        atomicStart = self.bs.tell()
        secData = self.bs.readBytes(sectionSize)
        bs = NoeBitStream(secData)
    
        # ---- Struct header ----
        chunkID   = bs.readUInt()
        structLen = bs.readUInt()
        version   = bs.readUInt()
    
        unk0      = bs.readUInt()
        triCount  = bs.readUInt()
        vertCount = bs.readUInt()
    
       
        # empty atomics, just skip
        if vertCount == 0 or triCount == 0:
            #print("Atomic %d: empty (no verts/tris) -> skipping" % atomicIndex)
            return
        
        print("Atomic %d: structLen=%d triCount=%d vertCount=%d" %
            (atomicIndex, structLen, triCount, vertCount))
            
        
        # skip vert header in all atomics
        vertStart = 56
        
        #print("Atomic %d: vertex start at local offset %d" % (atomicIndex, vertStart))
    
        # bounds check
        if vertStart + vertCount * 12 > len(secData):
            #print("Atomic %d: vertex buffer out of range -> skipping" % atomicIndex)
            return
    
        bs.seek(vertStart, NOESEEK_ABS)
        verts = bs.readBytes(vertCount * 12) 

    
        if not verts:
            #print("Atomic %d: failed to read vertex buffer -> skipping" % atomicIndex)
            return
    
        rapi.rpgBindPositionBuffer(verts, noesis.RPGEODATA_FLOAT, 12)
        
        # finished reading all vertices now are at the next section.
        # now try to find normals and vertex colors and uv map.
        
        normals = bs.readBytes(vertCount * 4)
        rapi.rpgBindNormalBuffer(normals, noesis.RPGEODATA_BYTE, 4)

        colors = bs.readBytes(vertCount * 4)
        rapi.rpgBindColorBuffer(colors, noesis.RPGEODATA_UBYTE, 4,4)

        uvs = bs.readBytes(vertCount * 8)
        rapi.rpgBindUV1BufferOfs(uvs, noesis.RPGEODATA_FLOAT, 8,0)



        # bin mesh contains face data and materials and shid.
        # ---- BinMeshPLG ----
        binMeshAbs = atomicStart + structLen + 24
        #print("Atomic %d BinMeshPLG offset: %d" % (atomicIndex, binMeshAbs))
    
        self.bs.seek(binMeshAbs, NOESEEK_ABS)
    
        cID  = self.bs.readUInt()
        cSize = self.bs.readUInt()
        cVer = self.bs.readUInt()
    
        #print("BinMesh header:", hex(cID), cSize, hex(cVer))
    
        if cID != 0x50E:
            #print("Atomic %d: Not BinMeshPLG -> skipping faces" % atomicIndex)
            return
    
        binData = self.bs.readBytes(cSize)
        bm = rBinMeshPLG(binData, matList, 1)
        bm.readFace()
    
    
    
    
    
    


class rwChunk(object):   
        def __init__(self,bs):
                self.chunkID,self.chunkSize,self.chunkVersion = struct.unpack("3I", bs.readBytes(12))
                self.version = libraryIDUnpackVersion(self.chunkVersion)
def libraryIDUnpackVersion( libid):

    if(libid & 0xFFFF0000):
        return (libid>>14 & 0x3FF00) + 0x30000 |(libid>>16 & 0x3F)
    return libid<<8

def readRWString(bs):
    rwStrChunk = rwChunk(bs)
    endOfs = bs.tell() + rwStrChunk.chunkSize
    string = bs.readString()   
    bs.seek(endOfs)
    return string
class rClump(object):
        def __init__(self,datas):
            self.bs = NoeBitStream(datas)
            self.mdlList = []
        def readClump(self):     
            rapi.rpgReset()         
            clumpStructHeader = rClumpStruct(self.bs)            
            framtListHeader = rwChunk(self.bs)
            datas = self.bs.readBytes(framtListHeader.chunkSize)
            frameList = rFrameList(datas)
            bones = frameList.readBoneList()
            skinBones = frameList.getSkinBones()
            geometryListHeader = rwChunk(self.bs)
            geometryListStructHeader = rwChunk(self.bs)
            geometryCount = self.bs.readUInt()
            if geometryCount:
                    datas = self.bs.readBytes(geometryListHeader.chunkSize-16)
            vertMatList=[0]*clumpStructHeader.numAtomics
            if clumpStructHeader.numAtomics:
                    atomicData = bytes()
                    for i in range(clumpStructHeader.numAtomics):
                            atomicHeader = rwChunk(self.bs)
                            atomicData += self.bs.readBytes(atomicHeader.chunkSize)
                    atomicList = rAtomicList(atomicData,clumpStructHeader.numAtomics).rAtomicStuct()
                    for j in range(clumpStructHeader.numAtomics):
                            vertMatList[atomicList[j].geometryIndex]= bones[atomicList[j].frameIndex].getMatrix()
            if geometryCount:
                    geometryList = rGeometryList(datas,geometryCount,vertMatList)
                    geometryList.readGeometry()                                
                    mdl = rapi.rpgConstructModel()
                    
                    texList = []  
                    texNameList = []
                    existTexNameList = []
                    path = rapi.getDirForFilePath(rapi.getInputName())
                    for m in range(len(geometryList.matList)):
                        texName = geometryList.matList[m].name
                        if texName not in texNameList:
                            texNameList.append(texName)                        
                            fullTexName = path+texName+".png"
                            if rapi.checkFileExists(fullTexName):            
                                texture = noesis.loadImageRGBA(fullTexName)
                                texList.append(texture)
                                existTexNameList.append(texName)
                    
                    matList = []
                    for i in range(len(texList)):
                            matName = existTexNameList[i]
                            material = NoeMaterial(matName, texList[i].name)
                            #material.setDefaultBlend(0)
                            matList.append(material)                    
                    mdl.setModelMaterials(NoeModelMaterials(texList,matList))
                    mdl.setBones(skinBones)
                    self.mdlList.append(mdl)
                    #rapi.rpgReset()  
            else:
                   mdl = NoeModel()
                   mdl.setBones(bones)
                   self.mdlList.append(mdl) 
class rClumpStruct(object):
        def __init__(self,bs):
                self.chunkID,self.chunkSize,self.chunkVersion = struct.unpack("3I", bs.readBytes(12))                
                self.numAtomics = bs.readUInt()
                self.numLights = bs.readUInt()
                self.numCameras = bs.readUInt()
class rFrameList(object):
        def __init__(self,datas):
                self.bs = NoeBitStream(datas)                
                self.frameCount = 0
                self.boneMatList=[]
                self.bonePrtIdList=[]
                self.boneIndexList=[]
                self.animBoneIDList=[]
                self.boneNameList=[]                
                self.hAnimBoneIDList =[]
                self.hSkinBoneIDList=[]                
                self.bones = []
                self.skinBones=[]
                self.hasHAnim = 0
                self.hasBoneName = 0
        def rFrameListStruct(self):
                header = rwChunk(self.bs)
                frameCount = self.bs.readUInt()
                self.frameCount = frameCount
                if frameCount:
                        for i in range(frameCount):
                                boneMat = NoeMat43.fromBytes(self.bs.readBytes(48)).transpose()
                                bonePrtId = self.bs.readInt()
                                self.bs.readInt()
                                self.boneMatList.append(boneMat)
                                self.bonePrtIdList.append(bonePrtId)
                                self.boneIndexList.append(i)

        def rHAnimPLG(self):
                hAnimVersion = self.bs.readInt()
                self.animBoneIDList.append(self.bs.readInt())
                boneCount = self.bs.readUInt()
                if boneCount:
                        self.hasHAnim = 1
                        flags = self.bs.readInt()
                        keyFrameSize = self.bs.readInt()
                        for i in range(boneCount):
                                # value = self.bs.readInt() & 0xffff
                                value = self.bs.readInt()
                                self.hAnimBoneIDList.append(value)
                                self.hSkinBoneIDList.append(self.bs.readInt())
                                boneType = self.bs.readInt()
        def readTString(self):
                outStr = ""
                strLen = self.bs.readInt()
                outStrBytes = self.bs.readBytes(strLen)
                outStr = outStrBytes[0:-1].decode('utf-8')
                return outStr                                
        def rUserDataPLG(self,index):
                numDirEntry = self.bs.readInt()
                boneName = "Bone"+str(index)
                for i in range(numDirEntry):
                        typeName = self.readTString()
                        userDataType = self.bs.readInt()
                        numberObjects = self.bs.readInt()
                        for o in range(numberObjects):
                            if userDataType == 1: self.bs.readInt()
                            elif userDataType == 2: self.bs.readFloat()
                            elif userDataType == 3:
                                outStr = self.readTString()
                                if typeName == "name" and o == 0 and i == 0:
                                    boneName = outStr
                self.boneNameList.append(boneName)
        def rFrameName(self,nameLength):
                boneName = ""
                boneNameBytes = self.bs.readBytes(nameLength);
                boneName = str(boneNameBytes, encoding = "utf-8")
                return boneName
        def rFrameExt(self,index):
                header = rwChunk(self.bs)
                endOfs = self.bs.tell() + header.chunkSize
                hasName = 0
                if header.chunkSize:
                        while (self.bs.tell()<endOfs):
                                chunk = rwChunk(self.bs)                                
                                if chunk.chunkID == 0x11e:
                                        self.rHAnimPLG()
                                elif chunk.chunkID == 0x253F2FE:  
                                        hasName = 1
                                        self.boneNameList.append(self.rFrameName(chunk.chunkSize))
                                        if self.hasBoneName != 1:
                                            self.hasBoneName = 1
                                elif chunk.chunkID == 0x11f:
                                        hasName = 1
                                        self.rUserDataPLG(index)
                                        if self.hasBoneName != 1:
                                            self.hasBoneName = 1
                                else:
                                        self.bs.seek(chunk.chunkSize,1)
                if(hasName==0):
                        if index==1:
                                self.boneNameList.append("RootBone")
                        else:
                                self.boneNameList.append("Bone"+str(index))
        def rFrameExtList(self):
                for i in range(self.frameCount):
                        self.rFrameExt(i)
        
        def readBoneList(self):
                self.rFrameListStruct()
                self.rFrameExtList()
                #Just list order
                bones=[]
                for i in range(self.frameCount):
                        boneIndex = i
                        boneName = self.boneNameList[i]
                        boneMat = self.boneMatList[i]
                        bonePIndex = self.bonePrtIdList[i]
                        bone = NoeBone(boneIndex, boneName, boneMat, None, bonePIndex)
                        bones.append(bone)
                        
                for i in range(self.frameCount):
                        bonePIndex = self.bonePrtIdList[i]
                        if(bonePIndex>-1):
                                prtMat=bones[bonePIndex].getMatrix()
                                boneMat = bones[i].getMatrix()                             
                                bones[i].setMatrix(boneMat * prtMat)
                self.bones = bones
                return bones
        def getSkinBones(self):      
                #编程思路
                #通过比较每个骨骼的AnimBoneID 和 hAnimBoneIDList 里面的 AnimBoneID 是否相同. AnimBoneID需要不等于-1(0xffff).
                #然后得到一个存在的AnimBoneID数组，SkinBoneID数组（未从0排序），frameListID数组（数组存储顺序ID，方便访问父级和名称，矩阵），父级骨骼ListID数组
                #通过遍历父级骨骼ListID数组，查看是否和frameListID数组相同，然后得到父级的SkinBoneID。链接父级。
                #根据skinBoneID从0开始重新排序. 本步骤不是必做，因为Noesis自动矫正列表,不过还是做了。
                #Programming ideas
                #By comparing the AnimBoneID of each bone and the AnimBoneID in hAnimBoneIDList are the same. AnimBoneID needs to be not equal to -1 (0xffff).
                #Then get an existing AnimBoneID array, SkinBoneID array (not sorted from 0), frameListID array (array storage order ID, easy to access parent and name, matrix), parent bone ListID array
                #By traversing the parent bone ListID array, check whether it is the same as the frameListID array, and then get the parent's SkinBoneID. Link to the parent.
                #Re-sort from 0 according to skinBoneID. This step is not necessary, because Noesis automatically corrects the list, but it is still done.                
                if self.hasHAnim > 0: 
                    boneDataList = []
                    for i in range(len(self.animBoneIDList)):
                        index = i
                        if len(self.animBoneIDList) == (self.frameCount - 1):
                            index = i + 1
                        elif len(self.animBoneIDList) == self.frameCount:
                            index = i                            
                        curBoneAnimBoneID = self.animBoneIDList[i]
                        if curBoneAnimBoneID != -1:
                            for j in range(len(self.hAnimBoneIDList)):
                                if curBoneAnimBoneID == self.hAnimBoneIDList[j]:
                                    boneData = skinBone()
                                    if self.hasBoneName == 1:
                                        boneData.boneName = self.boneNameList[index]
                                    else:                            
                                        boneData.boneName = "Bone" + str(curBoneAnimBoneID)
                                    boneData.matrix = self.bones[index].getMatrix()
                                    boneData.skinBoneID = self.hSkinBoneIDList[j]
                                    boneData.animBoneID = curBoneAnimBoneID
                                    boneData.listID = index
                                    boneData.listParentID = self.bonePrtIdList[index]
                                    boneDataList.append(boneData)
                    #find parent skin bone id
                    for i in range(len(boneDataList)):
                        for j in range(len(boneDataList)):
                            if boneDataList[i].listParentID == boneDataList[j].listID:
                                boneDataList[i].skinBoneParentID = boneDataList[j].skinBoneID
                            if len(self.animBoneIDList) == (self.frameCount - 1):
                                if boneDataList[i].listParentID == 0 :
                                    boneDataList[i].skinBoneParentID = -1
                                
                    #build skeleton
                    tempBones = []
                    for j in range(len(boneDataList)):                
                            boneIndex = boneDataList[j].skinBoneID
                            boneName =  boneDataList[j].boneName
                            boneMat = boneDataList[j].matrix
                            bonePIndex = boneDataList[j].skinBoneParentID
                            bone = NoeBone(boneIndex, boneName, boneMat, None,bonePIndex)
                            tempBones.append(bone)    
                    
                    #Re-sort from 0 according to skinBoneID.
                    bones = []
                    for i in range(len(boneDataList)): 
                            for j in range(len(boneDataList)):
                                if tempBones[j].index == i:
                                    bones.append(tempBones[j])

                    
                    self.skinBones = bones                   
                else:
                    bones = self.bones       
                return bones
class skinBone(object):
        def __init__(self):
            #self.bone = 0
            self.boneName = 0
            self.matrix = 0
            self.skinBoneID = 0
            self.animBoneID = 0
            self.skinBoneParentID = 0
            self.listID = 0
            self.listParentID = 0
            
class Atomic(object):
        def __init__(self):
               self.frameIndex = 0
               self.geometryIndex = 0
class rAtomicList(object):
        def __init__(self,datas,numAtomics):
               self.bs = NoeBitStream(datas)
               self.numAtomics = numAtomics
        def rAtomicStuct(self):
                atomicList=[]
                for i in range(self.numAtomics):
                        header = rwChunk(self.bs)
                        atomic = Atomic()
                        atomic.frameIndex = self.bs.readUInt()
                        atomic.geometryIndex = self.bs.readUInt()
                        flags = self.bs.readUInt()
                        unused = self.bs.readUInt()
                        extHeader = rwChunk(self.bs)
                        self.bs.seek(extHeader.chunkSize,1)
                        atomicList.append(atomic)
                return atomicList
                 
class rMatrial(object):
        def __init__(self,datas):
                self.bs = NoeBitStream(datas)   
                self.diffuseColor = NoeVec4([1.0, 1.0, 1.0, 1.0])
        def rMaterialStruct(self):
                header = rwChunk(self.bs)
                unused = self.bs.readInt()
                colorR = self.bs.readUByte()
                colorG = self.bs.readUByte() 
                colorB = self.bs.readUByte()
                colorA = self.bs.readUByte()
                self.diffuseColor = NoeVec4([colorR, colorG, colorB, colorA])
                unused2 = self.bs.readInt()
                hasTexture = self.bs.readInt()
                ambient = self.bs.readFloat()
                specular = self.bs.readFloat()
                diffuse = self.bs.readFloat()
                texName = ""
                if hasTexture:
                        texHeader = rwChunk(self.bs)
                        texStructHeader = rwChunk(self.bs)
                        textureFilter = self.bs.readByte()
                        UVAddressing = self.bs.readByte()
                        useMipLevelFlag = self.bs.readShort()
                        texName = noeStrFromBytes(self.bs.readBytes(rwChunk(self.bs).chunkSize))
                        #alphaTexName = noeStrFromBytes(self.bs.readBytes(rwChunk(self.bs).chunkSize))
                        self.bs.seek(rwChunk(self.bs).chunkSize,1)
                        texExtHeader = rwChunk(self.bs)
                        self.bs.seek(texExtHeader.chunkSize,1)
                matExtHeader = rwChunk(self.bs)
                self.bs.seek(matExtHeader.chunkSize,1)
                '''
                matExtEndOfs = self.bs.tell() + matExtHeader.chunkSize;
                if matExtHeader.chunkSize > 0:
                    while self.bs.tell() < matExtEndOfs:
                        chunk = rwChunk(self.bs)
                        self.bs.seek(chunk.chunkSize,NOESEEK_REL)
                '''                                                
                return texName
class rMaterialList(object):
        def __init__(self,datas):
                self.bs = NoeBitStream(datas)            
                self.matCount = 0
                self.matList = []
                self.texList = []
        def rMaterialListStruct(self):
                header = rwChunk(self.bs)
                self.matCount = self.bs.readUInt()
                self.bs.seek(self.matCount*4,1)
        def getMaterial(self):
                self.rMaterialListStruct()
                for i in range(self.matCount):
                        matData = self.bs.readBytes(rwChunk(self.bs).chunkSize)
                        mat = rMatrial(matData)
                        texName = mat.rMaterialStruct()                          
                        self.texList.append(texName)
                        if texName != "":                            
                            #matName = "material[%d]" %len(self.matList)
                            matName = texName
                            #matName = "mtl"+str(i)
                            material = NoeMaterial(matName, texName)
                            material.setDefaultBlend(0)
                            self.matList.append(material)                            
                        else:                            
                            matName = "mtl"+str(i)
                            material = NoeMaterial(matName, None)
                            material.setDiffuseColor(mat.diffuseColor)                            
                            self.matList.append(material)                            
                        #texture = NoeTexture()                        
                #return self.matList
class rGeometryList(object):
        def __init__(self,datas,geometryCount,vertMatList):
                self.bs = NoeBitStream(datas)            
                self.geometryCount = geometryCount
                self.vertMatList = vertMatList
                self.matList =[]
        def readGeometry(self):
                
                for i in range(self.geometryCount):
                        vertMat = self.vertMatList[i]
                        geometryHeader = rwChunk(self.bs)
                        datas = self.bs.readBytes(geometryHeader.chunkSize)
                        geo = rGeomtry(datas,vertMat)
                        # print("GEO ID:",i)
                        geo.rGeometryStruct()
                        for m in range(len(geo.matList)):
                                self.matList.append(geo.matList[m])                             
class rSkin(object):
        def __init__(self,datas,numVert,nativeFlag):
                self.bs = NoeBitStream(datas)
                self.numVert = numVert
                self.nativeFlag = nativeFlag
                self.boneIndexs = bytes()
                self.boneWeights = bytes()
                self.usedBoneIndexList = []
        def readSkin(self):
                if self.nativeFlag != 1:
                        boneCount = self.bs.readByte()
                        usedBoneIDCount=self.bs.readByte()
                        maxNumWeights = self.bs.readByte()
                        unk2 = self.bs.readByte()
                        self.bs.seek(usedBoneIDCount,1)
                        self.boneIndexs = self.bs.readBytes(self.numVert*4)
                        self.boneWeights= self.bs.readBytes(self.numVert*16)
                        rapi.rpgBindBoneIndexBuffer(self.boneIndexs, noesis.RPGEODATA_UBYTE, 4 , 4)
                        rapi.rpgBindBoneWeightBuffer(self.boneWeights, noesis.RPGEODATA_FLOAT, 16, 4)
                        inverseBoneMats=[]
                        for i in range(boneCount):
                                inverseBoneMats.append(NoeMat44.fromBytes(self.bs.readBytes(64)))                        
                        #self.bs.read('3f')

                else:
                        skinStruct = rwChunk(self.bs)
                        platform = self.bs.readUInt()
                        boneCount = self.bs.readUByte()
                        numUsedBone = self.bs.readUByte()
                        maxWeightsPerVertex = self.bs.readUByte()
                        padding = self.bs.readUByte()
                        self.usedBoneIndexList=[]
                        for i in range(numUsedBone):                            
                            self.usedBoneIndexList.append(self.bs.readUByte())      
                        inverseBoneMats=[]
                        for i in range(boneCount):
                                inverseBoneMats.append(NoeMat44.fromBytes(self.bs.readBytes(64)))
                        #self.bs.read('7i') #for ps2 dff


class rBinMeshPLG(object):
        def __init__(self,datas,matList,nativeFlag):
                self.bs = NoeBitStream(datas)
                self.matList = matList
                self.nativeFlag = nativeFlag
                self.matIdList = []
                self.matIdNumFaceList = []
        def readFace(self):
                faceType = self.bs.readInt() # 1 = triangle strip, 0 = triangle list
                numSplitMatID = self.bs.readUInt()
                indicesCount = self.bs.readUInt()
                for i in range(numSplitMatID):
                #for i in range(1): # FOR TESTING ONLY READ 1 MATERIAL SPLIT
                        faceIndices = self.bs.readUInt()
                        #print("num of face indices:", faceIndices)
                        
                        matID = self.bs.readUInt()
                        #print("mat id:", matID)
                        
                        self.matIdList.append(matID)
                        self.matIdNumFaceList.append(faceIndices)
                        
                        matName = self.matList[matID].name
                        rapi.rpgSetMaterial(matName)
                        
                        tristrips = self.bs.readBytes(faceIndices*4)
                        
                        # REMOVED CHECK FOR NATIVE FLAG!!
                        
                        if faceType == 1:
                            rapi.rpgCommitTriangles(tristrips, noesis.RPGEODATA_UINT, faceIndices, noesis.RPGEO_TRIANGLE_STRIP, 1)
                        elif faceType == 0:
                            rapi.rpgCommitTriangles(tristrips, noesis.RPGEODATA_UINT, faceIndices, noesis.RPGEO_TRIANGLE, 1)





class rNativeDataPLG(object):
        def __init__(self,datas,matList,binMeshPLG,vertMat):
                self.bs = NoeBitStream(datas)
                self.matList = matList
                self.matIdList = binMeshPLG.matIdList
                self.matIdNumFaceList = binMeshPLG.matIdNumFaceList
                self.vertMat = vertMat
        def readMesh(self):
                natvieStruct = rwChunk(self.bs)
                platform = self.bs.readUInt()
                splitCount = len(self.matIdList)
                for i in range(splitCount):
                    dataSize = self.bs.readUInt()
                    meshType = self.bs.readUInt()
                    endOfs = self.bs.tell() + dataSize
                    #vifEndOfs = endOfs
                    vifSize = dataSize
                    if meshType == 0:
                        strowCode = self.bs.readUInt()
                        VIFn_R0 = self.bs.readUInt()
                        VIFn_R1 = self.bs.readUInt()
                        VIFn_R2 = self.bs.readUInt()
                        VIFn_R3 = self.bs.readUInt()
                        #vifEndOfs = bs.tell() - 20 + VIFn_R0 * 16
                        vifSize = VIFn_R0 * 16
                        self.bs.seek(-20,NOESEEK_REL)
                    elif meshType == 1:
                        unpackVIF = self.bs.readUInt() 
                        vifSize = (unpackVIF & 0xffff) * 16 + 12                        
                    vertDatas = []
                    faceDatas = []
                    UVDatas =[]
                    normalDatas = []
                    skinBoneIDs = []
                    skinWeights = []
                    colorDatas = []            
                    vifData =  self.bs.readBytes(vifSize)
                    #unpackData = rapi.unpackPS2VIF(vifData)
                    
                    # i forgot why i added this check honestly
                    if vifData or len(vifData) < 32:
                        return False 
                    unpackData = rapi.unpackPS2VIF(vifData)
                    
                    
                    for up in unpackData:
                        if up.numElems == 3 and up.elemBits == 32:
                                vertDatas.append(up.data)    
                                faceDatas.append(getTriangleList(up.data))
                        elif up.numElems == 2 and up.elemBits == 32:
                                UVDatas.append(up.data)
                        elif up.numElems == 4 and up.elemBits == 8:
                                colorDatas.append(up.data) 
                        elif up.numElems == 3 and up.elemBits == 8:
                                normals = getNormal(up.data)
                                normalDatas.append(normals)                               
                    if meshType == 0:
                        for j in range(self.matIdNumFaceList[i]):
                            temp = bytearray(16)
                            for t in range(16):
                                temp[t] = self.bs.readUByte()                            
                            boneID1 = noeUnpack('B',temp[0:1])[0] # // 4
                            boneID2 = noeUnpack('B',temp[4:5])[0] # // 4
                            boneID3 = noeUnpack('B',temp[8:9])[0] # // 4
                            boneID4 = noeUnpack('B',temp[12:13])[0] # // 4
                            temp[0] = 0
                            temp[4] = 0
                            temp[8] = 0
                            temp[12] = 0                                   
                            weight1,weight2,weight3,weight4 = noeUnpack('4f',temp)
                            if (not len(normalDatas)) and (not len(UVDatas)) and (not len(colorDatas)):
                                if weight1 > 0:
                                    boneID1 = boneID1 // 3
                                    boneID1 -= 1
                                if weight2 > 0:
                                    boneID2 = boneID2 // 3
                                    boneID2 -= 1
                                if weight3 > 0:
                                    boneID3 = boneID3 // 3
                                    boneID3 -= 1
                                if weight4 > 0:
                                    boneID4 = boneID4 // 3
                                    boneID4 -= 1 
                            else:
                                if weight1 > 0:
                                    boneID1 = boneID1 // 4
                                    boneID1 -= 1
                                if weight2 > 0:
                                    boneID2 = boneID2 // 4
                                    boneID2 -= 1
                                if weight3 > 0:
                                    boneID3 = boneID3 // 4
                                    boneID3 -= 1
                                if weight4 > 0:
                                    boneID4 = boneID4 // 4
                                    boneID4 -= 1 
                            skinBoneIDs.append((boneID1,boneID2,boneID3,boneID4))
                            skinWeights.append((weight1,weight2,weight3,weight4))
                    paddingLength = endOfs - self.bs.tell()
                    self.bs.seek(paddingLength,NOESEEK_REL)
                    
                    #For triangle strips the last two vertices of the last triangle are used as the first two of the next one. 
                    #Similarly for line strips the last vertex of the last line segment is used as the first vertex for the next one. 
                    #In triangle and line lists every vertex is only used once.
                    numVertBlock = len(vertDatas)
                    skinDataIndex = 0
                    newSkinBoneIDs = []
                    newSkinWeights = []  
                    if meshType == 0:                  
                        for v in range(numVertBlock):           
                            stripNumVert = len(vertDatas[v])//12
                            boneIDs = bytes()
                            weights = bytes()
                            if v > 0:  
                                stripNumVert -= 2
                                w = 2
                                for j in range(w):
                                    boneID = skinBoneIDs[skinDataIndex-(w-j)]
                                    weight = skinWeights[skinDataIndex-(w-j)]
                                    boneIDs += noePack('4B',boneID[0],boneID[1],boneID[2],boneID[3])
                                    weights += noePack('4f',weight[0],weight[1],weight[2],weight[3])                            
                            for j in range(stripNumVert):                            
                                boneID = skinBoneIDs[skinDataIndex+j]
                                weight = skinWeights[skinDataIndex+j]
                                boneIDs += noePack('4B',boneID[0],boneID[1],boneID[2],boneID[3])
                                weights += noePack('4f',weight[0],weight[1],weight[2],weight[3])
                            skinDataIndex += stripNumVert                        
                            newSkinBoneIDs.append(boneIDs)
                            newSkinWeights.append(weights)    
                    #rapi.rpgSetName()                                
                    numVertBlock = len(vertDatas)
                    for v in range(numVertBlock):                        
                        vertBuffer = vertDatas[v]                        
                        vertBuffer = getTransformVertex(vertBuffer,self.vertMat)                  
                        rapi.rpgBindPositionBuffer(vertBuffer, noesis.RPGEODATA_FLOAT, 12)
                        
                        if meshType == 0:                            
                            rapi.rpgBindBoneIndexBuffer(newSkinBoneIDs[v], noesis.RPGEODATA_UBYTE, 4, 1)
                            rapi.rpgBindBoneWeightBuffer(newSkinWeights[v], noesis.RPGEODATA_FLOAT, 4, 1)  

                        if len(normalDatas):
                            normalData = normalDatas[v]                        
                            normalData = getTransformNormal(normalData,self.vertMat)
                            rapi.rpgBindNormalBuffer(normalData, noesis.RPGEODATA_FLOAT, 12)
                        if len(UVDatas):
                            UVData = UVDatas[v]
                            checkLODUV = noeUnpack("I",UVData[0:4])[0]                    
                            if checkLODUV != 0xE5E5E5E5:
                                rapi.rpgBindUV1Buffer(UVData, noesis.RPGEODATA_FLOAT, 8)                    

                        if len(colorDatas):
                            colorData = colorDatas[v]                
                            rapi.rpgBindColorBuffer(colorData, noesis.RPGEODATA_UBYTE, 4, 4)
                                             
                        matID = self.matIdList[i]
                        matName = self.matList[matID].name
                        rapi.rpgSetMaterial(matName)
                        if meshType == 0:
                            faceBuffer = faceDatas[v]
                            rapi.rpgCommitTriangles(faceBuffer, noesis.RPGEODATA_INT, len(faceBuffer)//4, noesis.RPGEO_TRIANGLE, 1)
                        else:
                            rapi.rpgCommitTriangles(None, noesis.RPGEODATA_INT, len(vertBuffer)//12, noesis.RPGEO_TRIANGLE_STRIP, 1)
                            
                        rapi.rpgClearBufferBinds()
def getTriangleList(vertBuffer):
    triangleList = []
    triangleDir = 1                        
    for j in range(len(vertBuffer)//12-2):
        v1 = noeUnpack('3f',vertBuffer[j*12:j*12+12])
        v2 = noeUnpack('3f',vertBuffer[(j+1)*12:(j+1)*12+12])
        v3 = noeUnpack('3f',vertBuffer[(j+2)*12:(j+2)*12+12])
        f1 = j
        f2 = j + 1
        f3 = j + 2
        if v1 != v2 and v2 != v3 and v1 != v3:
            if triangleDir > 0:
                triangleList.append((f1,f2,f3))
            else:
                triangleList.append((f2,f1,f3))
        triangleDir *= -1
    faceBuffer = bytes()
    for j in range(len(triangleList)):
        faceBuffer += noePack('3I',triangleList[j][0],triangleList[j][1],triangleList[j][2])    
    return faceBuffer
def getTransformVertex(vertBuffer,parentBoneMatrix):
    vin = NoeBitStream(vertBuffer)
    out = NoeBitStream()
    numVerts = len(vertBuffer) // 12
    for i in range(numVerts):
        vert = NoeVec3.fromBytes(vin.readBytes(12))
        vert *= parentBoneMatrix        
        out.writeBytes(vert.toBytes())
    return out.getBuffer()
def getUV(uvdata):
    uvin = NoeBitStream(uvdata)
    out = NoeBitStream()
    numVerts = len(uvdata) // 4
    for i in range(numVerts):
        u = uvin.readShort() / 4096.0
        v = uvin.readShort() / 4096.0
        out.writeFloat(u)
        out.writeFloat(v)
    return out.getBuffer()  
def getTransformNormal(normalData,parentBoneMatrix):
    nin = NoeBitStream(normalData)
    out = NoeBitStream()
    numVerts = len(normalData) // 12
    for i in range(numVerts):
        normal = NoeVec3.fromBytes(nin.readBytes(12))
        normal *= parentBoneMatrix
        normal.normalize()
        out.writeBytes(normal.toBytes())
    return out.getBuffer()
    
def getNormal(normalData):
    nin = NoeBitStream(normalData)
    out = NoeBitStream()
    numVerts = len(normalData) // 3
    for i in range(numVerts):
        nx = nin.readByte() / 128.0
        ny = nin.readByte() / 128.0
        nz = nin.readByte() / 128.0
        out.writeFloat(nx)
        out.writeFloat(ny)
        out.writeFloat(nz)        
    return out.getBuffer()
class rGeomtry(object):
        def __init__(self,datas,vertMat):
                self.bs = NoeBitStream(datas)
                self.vertMat = vertMat
                self.matList = []
        def rGeometryStruct(self):
                geoStruct = rwChunk(self.bs)
                FormatFlags = self.bs.readUShort()
                numUV = self.bs.readByte()
                nativeFlags = self.bs.readByte()
                numFace = self.bs.readUInt()
                numVert = self.bs.readUInt()
                numMorphTargets = self.bs.readUInt()
                Tristrip = FormatFlags % 2
                Meshes = (FormatFlags & 3) >> 1
                Textured = (FormatFlags & 7) >> 2
                Prelit = (FormatFlags & 0xF) >> 3
                Normals = (FormatFlags & 0x1F) >> 4
                Light = (FormatFlags & 0x3F) >> 5
                ModulateMaterialColor = (FormatFlags & 0x7F) >> 6
                Textured_2 = (FormatFlags & 0xFF) >> 7
                MtlIDList = []
                faceBuff = bytes()
                vertBuff = bytes()
                normBuff = bytes()
                uvs = None

                #spec
                if nativeFlags == 0 and numFace > 0:
                    Meshes = 1
                if nativeFlags != 1:
                        if (Prelit==1):
                                self.bs.seek(numVert*4,1)
                        if (Textured == 1):
                                uvs = self.bs.readBytes(numVert * 8)
                                rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
                        if (Textured_2==1):
                                uvs = self.bs.readBytes(numVert * 8)              
                                self.bs.seek(numVert*8,1)
                                rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
                        if (Meshes==1):                        
                                for i in range(numFace):
                                        f2 = self.bs.readBytes(2)
                                        f1 = self.bs.readBytes(2)
                                        MtlIDList.append(self.bs.readUShort())
                                        f3 = self.bs.readBytes(2)
                                        faceBuff+=f1
                                        faceBuff+=f2
                                        faceBuff+=f3                                
                sphereXYZ = NoeVec3.fromBytes(self.bs.readBytes(12))
                sphereRadius = self.bs.readFloat()
                positionFlag = self.bs.readUInt()
                normalFlag = self.bs.readUInt()
                if nativeFlags != 1:
                        #if (Meshes==1):
                        if positionFlag:
                                #vertBuff = self.bs.readBytes(numVert * 12)
                                for i in range(numVert):
                                        vert = NoeVec3.fromBytes(self.bs.readBytes(12))
                                        vert *= self.vertMat
                                        vertBuff+=vert.toBytes()
                                        rapi.rpgBindPositionBuffer(vertBuff, noesis.RPGEODATA_FLOAT, 12)
                        #if (Normals==1):
                        if normalFlag:
                                #normBuff = self.bs.readBytes(numVert * 12)
                                for i in range(numVert):
                                        normal = NoeVec3.fromBytes(self.bs.readBytes(12))
                                        normal *= self.vertMat
                                        normBuff+=normal.toBytes()        
                                        rapi.rpgBindNormalBuffer(normBuff, noesis.RPGEODATA_FLOAT, 12)
                matrialListHeader = rwChunk(self.bs)
                matDatas = self.bs.readBytes(matrialListHeader.chunkSize)
                rMatList = rMaterialList(matDatas)
                rMatList.getMaterial()
                matList = rMatList.matList
                texList = rMatList.texList
                for m in range(len(matList)):
                        self.matList.append(matList[m])
                geoExtHeader = rwChunk(self.bs)
                geoExtEndOfs = self.bs.tell()+geoExtHeader.chunkSize

                haveSkin = 0
                haveBinMesh = 0
                haveNavtiveMesh = 0
                while self.bs.tell()<geoExtEndOfs:
                        header = rwChunk(self.bs)
                        if header.chunkID == 0x50e:
                                haveBinMesh = 1
                                binMeshDatas = self.bs.readBytes(header.chunkSize)                    
                        elif header.chunkID == 0x116:
                                haveSkin = 1
                                skinDatas = self.bs.readBytes(header.chunkSize)
                        elif header.chunkID == 0x510:
                                haveNavtiveMesh = 1
                                nativeDatas = self.bs.readBytes(header.chunkSize)                                
                        else:
                             self.bs.seek(header.chunkSize,1)
                if haveSkin:
                        skin = rSkin(skinDatas,numVert,nativeFlags)
                        skin.readSkin()
                if haveBinMesh:
                        #binMeshPLG = rBinMeshPLG(binMeshDatas,matList,nativeFlags)
                        binMeshPLG = rBinMeshPLG(binMeshDatas,matList,0)
                        binMeshPLG.readFace()
                else:
                    faceList = [bytes()]*len(matList)
                    for f in range(len(faceBuff)//6):
                        face = struct.unpack('3H',faceBuff[f*6:f*6+6])
                        matID = MtlIDList[f]
                        faceList[matID] += struct.pack('3H',face[0],face[1],face[2])
                    for m in range(len(matList)):
                        matID = m
                        matName = self.matList[matID].name
                        rapi.rpgSetMaterial(matName)
                        faces = faceList[m]                        
                        rapi.rpgCommitTriangles(faces, noesis.RPGEODATA_USHORT, len(faces)//2, noesis.RPGEO_TRIANGLE, 1)                        
                if haveNavtiveMesh:
                        nativeDataPLG = rNativeDataPLG(nativeDatas,matList,binMeshPLG,self.vertMat)
                        nativeDataPLG.readMesh()
                #rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_USHORT, (numFace * 3), noesis.RPGEO_TRIANGLE, 1)
                rapi.rpgClearBufferBinds()
