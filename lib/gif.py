"""

A module for encoding data in the GIF format.
Built with reference to:
  http://www.w3.org/Graphics/GIF/spec-gif89a.txt
  http://en.wikipedia.org/wiki/Graphics_Interchange_Format

"""

import numpy
import lzw

def unsignedInt(n):
  return chr(n%256)+chr(n/256)

HEADER = "GIF89a"

def logicalScreenDescriptor(width,height,bitsPerColor=8):
  bytes = unsignedInt(width)
  bytes += unsignedInt(height)
  bytes += chr(128+(bitsPerColor-1)) # packed fields
  bytes += '\x00' # background color index
  bytes += '\x00' # aspect ratio (none given)
  return bytes

def applicationExtension(repetitions=0):
  bytes = "\x21\xFF\x0BNETSCAPE2.0\x03\x01"
  bytes += unsignedInt(repetitions if repetitions else 65535)
  bytes += '\x00' # end of block
  return bytes

def graphicsControlExtension(duration,transparency=None):
  bytes = "\x21\xF9\x04"
  bytes += '\x08' if transparency is None else '\x09'
  bytes += unsignedInt(duration)
  bytes += chr(transparency) if transparency else '\x00' 
  bytes += '\x00' # end of block
  return bytes

def imageDescriptor(width,height,left=0,top=0):
  bytes = '\x2C'
  bytes += unsignedInt(left) # image left position
  bytes += unsignedInt(top)  # image top position
  bytes += unsignedInt(width)
  bytes += unsignedInt(height)
  bytes += '\x00' # packed values
  return bytes

def blockData(data,blockSize=255):
  blocks = []
  while data:
    block, data = data[:blockSize], data[blockSize:]
    blocks.append(chr(len(block))+block)
  blocks.append(chr(0))
  return blocks

def parseIntFromFile(f):
  return ord(f.read(1))+256*ord(f.read(1))

def readDataBlocks(f):
  data = ""
  bytesToRead = ord(f.read(1))
  while bytesToRead:
    data += f.read(bytesToRead)
    bytesToRead = ord(f.read(1))
  return data

def readExtensionBlock(f):
  # assume we've just read '\x21' which opens extension block
  byte = f.read(1)
  if byte == "\xf9":
    # graphic control extension
    assert ord(f.read(1))==4
    packedFields = f.read(1)
    duration = parseIntFromFile(f)
    transparentColor = f.read(1)
    assert ord(f.read(1))==0
  elif byte=="\xfe":
    # comment extension block
    print readDataBlocks(f)
  elif byte=="\xff":
    # application extension block
    assert ord(f.read(1))==11
    print f.read(11)
    readDataBlocks(f)
  else:
    raise Exception()

def readImageBlock(f):
  # image descriptor
  leftPosition = parseIntFromFile(f)
  rightPosition = parseIntFromFile(f)
  width =  parseIntFromFile(f)
  height =  parseIntFromFile(f)
  packedFields = ord(f.read(1))
  localColorTable = packedFields>>7
  localColorTableSize = packedFields%8
  if localColorTable:
    colorTable = f.read(3*(2**(localColorTableSize+1)))
  codeSize = ord(f.read(1))
  data = readDataBlocks(f)
  imageData = lzw.decode(data,codeSize)

def readFromFile(filename):
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
    byte = f.read(1)
    while byte:
      if byte=="\x21":
        readExtensionBlock(f)
      elif byte=="\x2C":
        readImageBlock(f)
      elif byte=="\x3B":
        break
      else:
        print ord(byte)
        raise Exception()
      byte = f.read(1)

class GIF:
  def __init__(self,shape,duration=10,bitsPerColor=8,**kwargs):
    self.shape = shape
    self.colorTable = grayscaleColorTable(bitsPerColor)
    self.bitsPerColor = bitsPerColor
    self.frames = []
    self.duration = duration

  def addFrame(self,data,duration=None,box=None):
    if duration is None:
      duration = self.duration
    if box is None:
      box = [self.shape[0],self.shape[1],0,0]
    data = wrapReduceColor(data,2**self.bitsPerColor)
    self.frames.append(Frame(data,box,duration))

  def addRGBFrame(self,channels,duration=None,box=None,levels=[6,7,6]):
    if duration is None:
      duration = self.duration
    if box is None:
      box = [self.shape[0],self.shape[1],0,0]
    data = (levels[2]*levels[1]*wrapReduceColor(channels[0],levels[0])+
           levels[2]*wrapReduceColor(channels[1],levels[1])+
           wrapReduceColor(channels[2],levels[2])).astype(numpy.uint8)
    self.bitsPerColor = 8
    self.colorTable = makeReducedColorTable(levels)
    self.frames.append(Frame(data,box,duration))

  def save(self,filename):
    with open(filename,'wb') as f:
      f.write(HEADER)
      f.write(logicalScreenDescriptor(*self.shape,bitsPerColor=self.bitsPerColor))
      f.write(self.colorTable)
      f.write(applicationExtension(repetitions=0))
      for i,frame in enumerate(self.frames):
        f.write(graphicsControlExtension(int(frame.duration)))
        f.write(imageDescriptor(*frame.box))
        f.write(chr(self.bitsPerColor)) # code size
        data = lzw.encode(frame.imageData.ravel(),codeSize=self.bitsPerColor)
        f.write(''.join(blockData(data)))
      f.write('\x3b')

class Frame:
  def __init__(self,imageData,box,duration):
    self.imageData = imageData
    self.box = box
    self.duration = duration

import cutils

def wrapReduceColor(channel,levels):
  channel = channel.astype(numpy.double)
  return cutils.reduceColor(channel,levels)  

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

if __name__ == '__main__':
  dimensions = (200,200)
  g = GIF(dimensions,bitsPerColor=2)
  for i in range(256):
    g.addFrame(i+numpy.zeros(dimensions),duration=10)
  g.save("test.gif")



