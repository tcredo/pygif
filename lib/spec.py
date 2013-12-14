"""

This file contains a bunch of constants and convenience classes for working with GIF files. 

"""

HEADER = "GIF89a"

TRAILER = "\x3b"

EXTENSION_INTRODUCER = "\x21"
                            
APPLICATION_EXTENSION_BLOCK = "\x21\xFF\x0BNETSCAPE2.0\x03\x01%s\x00"

GRAPHICS_CONTROL_EXTENSION = "\x21\xF9\x04"+\
                             "%(packed_fields)s"+\
                             "%(duration)s"+\
                             "%(transparent_color_index)s\x00"

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

