"""

A module for encoding data in the GIF format.
Built with reference to:
  http://www.w3.org/Graphics/GIF/spec-gif89a.txt
  http://en.wikipedia.org/wiki/Graphics_Interchange_Format

"""

import numpy, math
import lzw, cutils

HEADER = "GIF89a"
TRAILER = "\x3b"
LOGICAL_SCREEN_DESCRIPTOR = "%(width)s"+\
                            "%(height)s"+\
                            "%(packed_fields)s"+\
                            "%(background_color_index)s"+\
                            "%(aspect_ratio)s"
APPLICATION_EXTENSION_BLOCK = "\x21\xFF\x0BNETSCAPE2.0\x03\x01%s\x00"
GRAPHICS_CONTROL_EXTENSION = "\x21\xF9\x04"+\
                             "%(packed_fields)s"+\
                             "%(duration)s"+\
                             "%(transparent_color_index)s\x00"
IMAGE_DESCRIPTOR = "\x2C%(left)s%(top)s%(width)s%(height)s%(packed_fields)s"

def uInt(n):
  """Encode an integer as two bytes."""
  return chr(n%256)+chr(n/256)

def parseIntFromFile(f):
  """Read two bytes from a file object and interpret as an unsigned int."""
  return ord(f.read(1))+256*ord(f.read(1))

class DataBlock:
  """Convenience class for representing raw data blocks from a GIF file."""
  def __init__(self,data):
    self.data = data

  def toFile(self,f,blockSize=255):
    data = self.data[:]
    while data:
      block, data = data[:blockSize], data[blockSize:]
      f.write(chr(len(block))+block)
    f.write(chr(0))

  @staticmethod
  def fromFile(f):
    data = ""
    bytesToRead = ord(f.read(1))
    while bytesToRead:
      data += f.read(bytesToRead)
      bytesToRead = ord(f.read(1))
    return DataBlock(data)

def grayscaleColorTable(bits=8):
  conversion = 255./(2**bits-1)
  return ''.join([3*chr(int(conversion*i)) for i in range(2**bits)])

def makeReducedColorTable(levels):
  assert len(levels)==3
  assert levels[0]*levels[1]*levels[2]<256
  conversions = [255./(l-1) for l in levels]
  colorTable = [(int(conversions[0]*r),int(conversions[1]*g),int(conversions[2]*b))
                for r in range(levels[0]) for g in range(levels[1]) for b in range(levels[2])]
  colorTable = ''.join([chr(r)+chr(g)+chr(b) for r,g,b in colorTable])
  colorTable += chr(0)*3*(256-len(colorTable)/3)
  return colorTable

def wrapReduceColor(channel,levels):
  channel = channel.astype(numpy.double)
  return cutils.reduceColor(channel,levels)  

class GIF:
  def __init__(self,shape,duration=10,bitsPerColor=8,**kwargs):
    self.shape = shape
    self.globalColorTable = grayscaleColorTable(bitsPerColor)
    self.bitsPerColor = bitsPerColor
    self.graphicBlocks = []
    self.duration = duration

  def addFrameFromNumpyData(self,data,duration=None,colorTable=None):
    if duration is None:
      duration = self.duration
    data = wrapReduceColor(data,2**self.bitsPerColor)
    self.graphicBlocks.append(GraphicBlock(data,self.shape,duration,bitsPerColor=self.bitsPerColor))

  def addRGBFrame(self,channels,duration=None,levels=[6,7,6]):
    if duration is None:
      duration = self.duration
    data = (levels[2]*levels[1]*wrapReduceColor(channels[0],levels[0])+
           levels[2]*wrapReduceColor(channels[1],levels[1])+
           wrapReduceColor(channels[2],levels[2])).astype(numpy.uint8)
    self.bitsPerColor = 8
    self.colorTable = makeReducedColorTable(levels)
    self.graphicBlocks.append(GraphicBlock(data,self.shape,duration))

  def save(self,filename,loops=0):
    with open(filename,'wb') as f:
      f.write(HEADER)
      f.write(LOGICAL_SCREEN_DESCRIPTOR
                  % {"width":uInt(self.shape[0]),
                     "height":uInt(self.shape[1]),
                     "packed_fields":chr(128+(self.bitsPerColor-1)),
                     "background_color_index":'\x00',
                     "aspect_ratio":'\x00'})
      f.write(self.globalColorTable)
      f.write(APPLICATION_EXTENSION_BLOCK % uInt(loops if loops else 65535))
      for graphicBlock in self.graphicBlocks:
        graphicBlock.toFile(f)
      f.write(TRAILER)
      
  @staticmethod
  def fromFile(filename):
    with open(filename,'rb') as f:
      assert f.read(6)==HEADER
      # logical screen descriptor
      width = parseIntFromFile(f)
      height = parseIntFromFile(f)
      packedFields = ord(f.read(1))
      globalColorTable = packedFields>>7
      globalColorTableSize = packedFields%8
      backgroundColorIndex = f.read(1)
      aspectRatio = f.read(1)
      # global color table
      if globalColorTable:
        colorTable = f.read(3*(2**(globalColorTableSize+1)))
      # other blocks
      frames = []
      byte = f.read(1)
      while byte:
        if byte=="\x21": # extension block
          byte = f.read(1)
          if byte == "\xf9": # graphic control extension
            assert ord(f.read(1))==4
            packedFields = f.read(1)
            duration = parseIntFromFile(f)
            transparentColor = f.read(1)
            print transparentColor
            assert ord(f.read(1))==0
          elif byte=="\xfe": # comment extension block
            print DataBlock.fromFile(f).data
          elif byte=="\xff": # application extension block
            assert ord(f.read(1))==11
            print f.read(11)
            DataBlock.fromFile(f)
          else:
            raise Exception()
        elif byte=="\x2C":
          graphicBlocks.append(GraphicBlock.fromFile(f))
        elif byte=="\x3B":
          break
        else:
          print ord(byte)
          raise Exception()
        byte = f.read(1)
    g = GIF((width,height),bitsPerColor=globalColorTableSize+1)
    g.globalColorTable = colorTable
    g.graphicBlocks = graphicBlocks
    return g

class GraphicBlock:
  def __init__(self,imageData,shape,duration,**kwargs):
    self.imageData = imageData
    self.shape = shape
    self.duration = duration
    self.colorTable = kwargs.get("colorTable",None)
    self.bitsPerColor = kwargs.get("bitsPerColor",8)
    
  def toFile(self,f,transparency=None):
    f.write(GRAPHICS_CONTROL_EXTENSION
                % {"packed_fields":'\x08' if transparency is None else '\x09',
                   "duration":uInt(int(self.duration)),
                   "transparent_color_index":chr(transparency) if transparency else '\x00'})
    colorTableSize = None
    if self.colorTable:
      colorTableSize = int(math.log(len(self.colorTable)/3,2))
      packed_fields = chr((1<<7)+colorTableSize-1)
    else:
      packed_fields = "\x00"
    f.write(IMAGE_DESCRIPTOR
                % {"left":uInt(0),
                   "top":uInt(0),
                   "width":uInt(self.shape[0]),
                   "height":uInt(self.shape[1]),
                   "packed_fields":packed_fields})
    if self.colorTable:
      f.write(self.colorTable)
    # table based image data
    codesize = self.bitsPerColor if colorTableSize is None else max(2,colorTableSize)
    f.write(chr(codesize)) # code size
    data = lzw.encode(self.imageData.ravel(),codeSize=codesize)
    DataBlock(data).toFile(f)
    
  @staticmethod
  def fromFile(f):
    leftPosition = parseIntFromFile(f)
    topPosition = parseIntFromFile(f)
    width = parseIntFromFile(f)
    height = parseIntFromFile(f)
    packedFields = ord(f.read(1))
    localColorTable = packedFields>>7
    localColorTableSize = packedFields%8
    if localColorTable:
      colorTable = f.read(3*(2**(localColorTableSize+1)))
    codeSize = ord(f.read(1))
    data = DataBlock.fromFile(f).data
    imageData = numpy.array([ord(c) for c in lzw.decode(data,codeSize)])
    return GraphicBlock(imageData,[width,height],10)

if __name__ == '__main__':
  dimensions = (200,200)
  g = GIF(dimensions,bitsPerColor=2)
  for i in range(256):
    g.addFrameFromNumpyData(i+numpy.zeros(dimensions),duration=10)
  g.save("test.gif")



