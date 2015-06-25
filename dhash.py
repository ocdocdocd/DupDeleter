from PIL import Image
import logging


#######################################################################
#
# DHash
#
# Implements the DHash image comparison algorithm.
#
# Ryan C Murray
#
#######################################################################


def loadImg(loc):
    '''
    Loads and returns image data from LOCATION
    '''
    try:
        return Image.open(loc)
    except:
        logging.warning("Could not open image.")
        return None


def shrinkAndGray(img, Xdim=9, Ydim=8):
    '''
    shrink(image, [Xdim, Ydim]) -> image

    First converts img to grayscale, then shrinks img down to given
    dimensions. If no dimensions are given then it defaults to 9x8.
    '''
    im = img.convert("L")
    return im.resize((Xdim, Ydim))


def getBits(img):
    '''
    getBits(img) -> binary int

    Computes a bitboard based on pixel intensity differences in the
    image. Returned board will be equal in length to the number of
    pixels in each row - 1 times the number of rows. For example,
    a 9x8 image will return a bitboard of length 64.

    1 indicates the left pixel is brighter than the right pixel.
    0 indicates the right pixel is brighter than the left pixel.
    '''
    pixels = list(img.getdata())
    cols, rows = img.size
    bitboard = 0b0

    pixels2d = [[pixels[(i * 9) + j] for j in xrange(cols)] for i in xrange(rows)]

    for row in pixels2d:
        for i in xrange(cols - 1):
            bitboard <<= 1
            if row[i] > row[i + 1]:
                bitboard |= 1

    return bitboard


def compare(img1, img2):
    '''
    compare(img1, img2) -> int

    Compares two shrunk, grayscaled images pixel-by-pixel and returns
    an int value indicating the number of pixels that differ. Images
    must have identical diemnsions.
    '''
    degree = 0
    size = img1.size
    if size != img2.size:
        logging.error("Images are not the same dimensions")
        return
    bit_board_1 = getBits()  # bit board for image 1
    bit_board_2 = getBits()  # bit board for image 2

    diff = bit_board_1 ^ bit_board_2  # xor to find unique bits

    for i in xrange(size[0] - 1 * size[1]):
        if diff >> i:
            degree += 1

    return degree


def isSimilar(degree, threshold=10):
    '''
    isSimilar(degree [, threshold]) -> Boolean

    Takes in a degree of similarity value. If values is less than or
    equal to threshold then returns True. Else, False.
    '''
    return degree <= threshold


def hash(loc):
    '''
    Returns a hash (bitboard) of the image at loc.
    '''
    try:
        im = loadImg(loc)
        im = shrinkAndGray(im)
        return getBits(im)
    except:
        return -1
