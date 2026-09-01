"""
Fake audioop module for Python 3.14 compatibility.
"""

def add(a, b):
    return a + b

def adpcm2lin(adpcmfragment, width, state):
    return b'', (0, 0)

def alaw2lin(fragment, width):
    return b''

def avg(data, size):
    return 0

def avgpp(data, size):
    return 0

def bias(data, size, bias):
    return data

def cross(data, size):
    return 0

def findfactor(data, size):
    return 0

def findfit(data, size, code):
    return 0, 0

def findmax(data, size):
    return 0, 0

def getsample(data, size, index):
    return 0

def lin2adpcm(data, width, state):
    return b'', (0, 0)

def lin2alaw(data, width):
    return b''

def lin2lin(data, width, newwidth):
    return data

def lin2ulaw(data, width):
    return b''

def max(data, size):
    return 0

def maxpp(data, size):
    return 0

def minmax(data, size):
    return 0, 0

def mul(data, size, factor):
    return data

def ratecv(data, size, nchannels, inrate, outrate, state, weightA, weightB):
    return data, state

def reverse(data, size):
    return data[::-1]

def rms(data, size):
    return 0

def tomono(data, size, fac1, fac2):
    return data

def tostereo(data, size, fac1, fac2):
    return data

def ulaw2lin(data, width):
    return b''

def byteswap(data, size):
    return data

def lin2adpcm(data, width, state):
    return b'', (0, 0)

def adpcm2lin(data, width, state):
    return b'', (0, 0)

def lin2alaw(data, width):
    return b''

def alaw2lin(data, width):
    return b''

def lin2ulaw(data, width):
    return b''

def ulaw2lin(data, width):
    return b''
