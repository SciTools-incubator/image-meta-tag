'''
Created on 13 Aug 2015

@author: freb
'''

import os

class ImageDict():
    '''
    A class which holds a heirachical dictionary of dictionaries, and the associated
    methods for appending/removing dictionaries from it.
    
    The expected use case for the dictionary is to represent a large set of images, 
    which can be organised by their metadata tags.
    
    When used in this way, the ImageDict class also contains methods which write out
    web page interfaces for browsing the images. 
    '''

    def __init__(self):
        pass


def readmeta_from_image(img_file, img_format=None):
    'Reads the metadata added by the ImageMetaTag savefig, from an image file'

    if img_format is None:
        # get the img_format from the end of the filename
        _, img_format = os.path.splitext(img_file)
        if img_format is None or img_format == '':
            raise ValueError('Cannot determine file img_format to read from filename "%s"' % filename)
        # get rid of the . to be consistent throughout
        img_format = img_format[1:]
    else:
        if img_format.startswith('.'):
            img_format = img_format[1:]

    if img_format == 'png':
        try:
            img_obj = Image.open(img_file)
            img_info = img_obj.info
            read_ok = True
        except:
            read_ok = False
            img_info = None
    else:
        raise NotImplementedError('Currently, ImageMetaTag does not support "%s" format images' % img_format)
    
    return (read_ok, img_info)

def read_imgfile_info(filename):
    'extracts the stored info/metadata of an image file'
    img_obj = Image.open(filename)
    info = img_obj.info
    return info
