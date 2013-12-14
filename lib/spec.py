"""

This file contains a bunch of constants and convenience classes for working with GIF files. 

"""

HEADER = "GIF89a"

TRAILER = "\x3b"

EXTENSION_INTRODUCER = "\x21"

COMMENT_EXTENSION_LABEL = "\xfe"

def uInt(n):
  """Encode an integer as two bytes."""
  return chr(n%256)+chr(n/256)

def parseIntFromFile(f):
  """Read two bytes from a file object and interpret as an unsigned int."""
  return ord(f.read(1))+256*ord(f.read(1))

class LogicalScreenDescriptor:
  """A convenience class for reading and writing screen descriptor blocks."""
  def __init__(self,width,height,**kwargs):
    self.width = width
    self.height = height
    self.packed_fields = kwargs.get("packed_fields",135)
    self.background_color_index = kwargs.get("background_color_index",0)
    self.aspect_ratio = kwargs.get("aspect_ratio",0)

  def toFile(self,f):
    f.write(uInt(self.width)+
            uInt(self.height)+
            chr(self.packed_fields)+
            chr(self.background_color_index)+
            chr(self.aspect_ratio))
  
  @staticmethod
  def fromFile(f):
    w = parseIntFromFile(f)
    h = parseIntFromFile(f)
    pf = ord(f.read(1))
    bci = ord(f.read(1))
    ar = ord(f.read(1))
    return LogicalScreenDescriptor(w,h,packed_fields=pf,
                                   background_color_index=bci,
                                   aspect_ratio=ar)
                                   
class ApplicationExtension:
  """A convenience class for application extension blocks."""
  LABEL = "\xff"
  
  def __init__(self,repeat):
    self.repeat = repeat
    
  def toFile(self,f):
    f.write(EXTENSION_INTRODUCER+
            self.LABEL+
            "\x0BNETSCAPE2.0\x03\x01"+
            uInt(self.repeat)+
            "\x00")

  @staticmethod    
  def fromFile(f):
    # Assume that EXTENSION_INTRODUCER and LABEL have already been read.
    assert ord(f.read(1))==11           # fixed block size
    assert f.read(11)=="NETSCAPE2.0"    # application id and authentication
    assert ord(f.read(1))==3            # data block size
    assert f.read(1)=="\x01"            # fixed byte
    repeat = parseIntFromFile(f)        # repetitions
    assert f.read(1)=="\x00"            # block terminator
    return ApplicationExtension(repeat)
  

class GraphicControlExtension:
  """A convenience class for graphic control extension blocks."""
  LABEL = "\xF9"

  def __init__(self,duration,**kwargs):
    self.packed_fields = kwargs.get("packed_fields",8)
    self.duration = duration
    self.transparent_color_index = kwargs.get("transparent_color_index",0)
    
  def toFile(self,f):
    f.write(EXTENSION_INTRODUCER+
            self.LABEL+
            "\x04"+  # block size
            chr(self.packed_fields)+
            uInt(self.duration)+
            chr(self.transparent_color_index)+
            "\x00")  # block terminator

  @staticmethod
  def fromFile(f):
    # Assume that EXTENSION_INTRODUCER and LABEL have already been read.
    assert f.read(1)=="\x04"
    pf = ord(f.read(1))
    duration = parseIntFromFile(f)
    tci = ord(f.read(1))
    assert f.read(1)=="\x00"
    return GraphicControlExtension(duration,packed_fields=pf,
                                   transparent_color_index=tci)

class ImageDescriptor:
  """A convenience class for reading and writing image descriptor blocks."""
  IMAGE_SEPARATOR = "\x2C"
  
  def __init__(self,width,height,left=0,top=0,packed_fields=0):
    self.left = left
    self.top = top
    self.width = width
    self.height = height
    self.packed_fields = packed_fields
  
  def toFile(self,f):
    f.write(self.IMAGE_SEPARATOR+
            uInt(self.left)+
            uInt(self.top)+
            uInt(self.width)+
            uInt(self.height)+
            chr(self.packed_fields))
  
  @staticmethod
  def fromFile(f):
    # Assume that IMAGE_SEPARATOR has just been read.
    l = parseIntFromFile(f)
    t = parseIntFromFile(f)
    w = parseIntFromFile(f)
    h = parseIntFromFile(f)
    pf = ord(f.read(1))
    return ImageDescriptor(w,h,left=l,top=t,packed_fields=pf)

class DataBlock:
  """A convenience class for representing raw data blocks."""
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

