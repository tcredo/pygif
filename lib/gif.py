"""

A module for encoding data in the GIF format.
Built with reference to:
  http://www.w3.org/Graphics/GIF/spec-gif89a.txt
  http://en.wikipedia.org/wiki/Graphics_Interchange_Format

"""

import numpy, math
import lzw, cutils

HEADER = "GIF89a"

def unsignedInt(n):
  return chr(n%256)+chr(n/256)

def parseIntFromFile(f):
  return ord(f.read(1))+256*ord(f.read(1))

def blockData(data,blockSize=255):
  blocks = []
  while data:
    block, data = data[:blockSize], data[blockSize:]
    blocks.append(chr(len(block))+block)
  blocks.append(chr(0))
  return blocks

def readDataBlocks(f):
  data = ""
  bytesToRead = ord(f.read(1))
  while bytesToRead:
    data += f.read(bytesToRead)
    bytesToRead = ord(f.read(1))
  return data

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
    self.colorTable = grayscaleColorTable(bitsPerColor)
    self.bitsPerColor = bitsPerColor
    self.frames = []
    self.duration = duration

  def addFrame(self,data,duration=None,colorTable=None):
    if duration is None:
      duration = self.duration
    data = wrapReduceColor(data,2**self.bitsPerColor)
    self.frames.append(Frame(data,self.shape,duration))

  def addRGBFrame(self,channels,duration=None,levels=[6,7,6]):
    if duration is None:
      duration = self.duration
    data = (levels[2]*levels[1]*wrapReduceColor(channels[0],levels[0])+
           levels[2]*wrapReduceColor(channels[1],levels[1])+
           wrapReduceColor(channels[2],levels[2])).astype(numpy.uint8)
    self.bitsPerColor = 8
    self.colorTable = makeReducedColorTable(levels)
    self.frames.append(Frame(data,self.shape,duration))

  def save(self,filename):
    with open(filename,'wb') as f:
      f.write(HEADER)
      # logical screen descriptor
      f.write(unsignedInt(self.shape[0]))
      f.write(unsignedInt(self.shape[1]))
      f.write(chr(128+(self.bitsPerColor-1))) # packed fields
      f.write('\x00') # background color index
      f.write('\x00') # aspect ratio (none given)
      # global color table
      f.write(self.colorTable)
      # application extension block
      repetitions=0
      f.write("\x21\xFF\x0BNETSCAPE2.0\x03\x01")
      f.write(unsignedInt(repetitions if repetitions else 65535))
      f.write('\x00')
      # image data
      for i,frame in enumerate(self.frames):
        frame.writeToFile(f,self.bitsPerColor)
      f.write('\x3b') # trailer

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
            print readDataBlocks(f)
          elif byte=="\xff": # application extension block
            assert ord(f.read(1))==11
            print f.read(11)
            readDataBlocks(f)
          else:
            raise Exception()
        elif byte=="\x2C":
          frames.append(Frame.fromFileData(f))
        elif byte=="\x3B":
          break
        else:
          print ord(byte)
          raise Exception()
        byte = f.read(1)
    g = GIF((width,height),bitsPerColor=globalColorTableSize+1)
    g.colorTable = colorTable
    g.frames = frames
    return g

class Frame:
  def __init__(self,imageData,shape,duration,**kwargs):
    self.imageData = imageData
    self.shape = shape
    self.duration = duration
    self.colorTable = kwargs.get("colorTable",None)
    
  def writeToFile(self,f,bitsPerColor):
    # graphics control extension
    transparency=None
    f.write("\x21\xF9\x04")
    f.write('\x08' if transparency is None else '\x09')
    f.write(unsignedInt(int(self.duration)))
    f.write(chr(transparency) if transparency else '\x00')
    f.write('\x00')
    # image descriptor
    f.write('\x2C')
    f.write(unsignedInt(0)) # image left position
    f.write(unsignedInt(0))  # image top position
    f.write(unsignedInt(self.shape[0]))
    f.write(unsignedInt(self.shape[1]))
    # local color table
    colorTableSize = None
    if self.colorTable:
      colorTableSize = int(math.log(len(self.colorTable)/3,2))
      packedValues = chr((1<<7)+colorTableSize-1)
      f.write(packedValues)
      f.write(self.colorTable)
    else:
      f.write('\x00') # packed values
    # table based image data
    codesize = bitsPerColor if colorTableSize is None else max(2,colorTableSize)
    f.write(chr(codesize)) # code size
    data = lzw.encode(self.imageData.ravel(),codeSize=codesize)
    f.write(''.join(blockData(data)))
    
  @staticmethod
  def fromFileData(f):
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
    data = readDataBlocks(f)
    imageData = numpy.array([ord(c) for c in lzw.decode(data,codeSize)])
    return Frame(imageData,[width,height],10)

if __name__ == '__main__':
  dimensions = (200,200)
  g = GIF(dimensions,bitsPerColor=2)
  for i in range(256):
    g.addFrame(i+numpy.zeros(dimensions),duration=10)
  g.save("test.gif")



