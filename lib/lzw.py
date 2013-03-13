"""

An implementation of Lempel-Ziv-Welch (LZW) compression.
For more information, see:
  http://en.wikipedia.org/wiki/Lempel-Ziv-Welch

"""

# TODO: FIND SOME WAY TO REFACTOR THIS TO MAKE IT CLEARER

MAXIMUM_CODE_SIZE = 12

def encode(data,codeSize=8):
  """ LZW coding. """
  codeTable = dict([(chr(n),n) for n in range(1<<codeSize)])
  CLEAR = 1<<codeSize
  END = CLEAR+1
  nextAvailableCode = END+1
  bb = bitBuffer(codeSize)
  localString = ""
  bb.pack(CLEAR)
  for character in data: 
    character = chr(character)
    if localString+character in codeTable:
      localString += character
    else:
      bb.pack(codeTable[localString])
      codeTable[localString+character] = nextAvailableCode
      nextAvailableCode += 1
      localString = character
      if nextAvailableCode>>MAXIMUM_CODE_SIZE:
        bb.pack(CLEAR)
        codeTable = dict([(chr(n),n) for n in range(1<<codeSize)])
        nextAvailableCode = END+1
  bb.pack(codeTable[localString])
  bb.pack(END)
  bytes = bb.flush()
  return bytes

class bitBuffer:
  """ Packs codes into bytes. """
  def __init__(self,codeSize=8):
    self.codeSize = codeSize
    self.bits = 0
    self.nBits = 0
    self.bytes = ""
    self.highestCode = (1<<self.codeSize)+1
    self.bitsPerCode = self.codeSize+1

  def pack(self,code):
    self.bits += code << self.nBits
    self.nBits += self.bitsPerCode
    while self.nBits>7:
      self.bytes += chr(self.bits%256)
      self.bits >>= 8
      self.nBits -= 8
    if code==1<<self.codeSize: # CLEAR code
      self.highestCode = (1<<self.codeSize)+1
      self.bitsPerCode = self.codeSize+1
    else:
      self.highestCode += 1
      if self.highestCode>>self.bitsPerCode:
        self.bitsPerCode += 1

  def flush(self):
    if self.nBits:
      self.bytes += chr(self.bits)
      self.bits = 0
      self.nBits = 0
    return self.bytes

def decode(data,codeSize=8):
  """LZW decoding."""
  codeTable = dict([(n,chr(n)) for n in range(1<<codeSize)])
  CLEAR = 1<<codeSize
  END = CLEAR+1
  nextAvailableCode = END+1
  decodedBytes = ""
  lastOutput = ""
  for code in unpackCodes(data,codeSize=codeSize):
    if code==CLEAR:
      codeTable = dict([(n,chr(n)) for n in range(1<<codeSize)])
      nextAvailableCode = END+1
      lastOutput = ""
    elif code==END:
      break
    elif code==nextAvailableCode:
      # if nextAvailableCode is used we immediately saw last formed code
      result = lastOutput+lastOutput[0] # compute this because code not in table
      codeTable[nextAvailableCode] = result
      nextAvailableCode += 1
      lastOutput = result
      decodedBytes += result
    else:
      result = codeTable[code]
      if lastOutput and not nextAvailableCode>>MAXIMUM_CODE_SIZE:
        codeTable[nextAvailableCode] = lastOutput+result[0]
        nextAvailableCode += 1
      lastOutput = result
      decodedBytes += result
  return decodedBytes

def unpackCodes(data,codeSize=8):
  """A generator that yields codes from packed bytes."""
  bits = 0
  nBits = 0
  CLEAR = 1<<codeSize
  highestCode = CLEAR+1
  bitsPerCode = codeSize+1
  while 8*len(data)+nBits>=bitsPerCode:
    while nBits<bitsPerCode:
      character, data = data[0], data[1:]
      character = ord(character)
      bits += character << nBits
      nBits += 8
    code = bits%(1<<bitsPerCode)
    bits >>= bitsPerCode
    nBits -= bitsPerCode
    if code==CLEAR:
      highestCode = CLEAR+1
      bitsPerCode = codeSize+1
    else:
      if highestCode<2**MAXIMUM_CODE_SIZE-1:
        highestCode += 1
        if highestCode>>bitsPerCode:
          bitsPerCode += 1
    yield code

