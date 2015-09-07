'''
Module containing a wrapper for matplotlib.pyplot.savefig, which adds image metadata taggging
and basic image maniupulation.
'''

import os
import matplotlib.pyplot as plt

# image manipulations:
import Image, ImageChops
from PIL import PngImagePlugin

def savefig(filename, img_format=None, img_converter=0, do_trim=False, verbose=False, img_tags=None, \
                 keep_open=False, dpi=None):
    '''
    Little routine to wrap over savefig, to include file size optimisation and png image tagging
    
    The filesize optimisation depends on the img_converter input passes into image_file_postproc
    
    Args:  filename (can include the file extension, or that can be specified as the img_format option)
           
    Options: 
      img_format : (usually without the '.'. Currently only the png file img_format is supported for tagging/conversion).
    
      img_converter: this sets the level of image maniupulation, which can be done
                     at the same time as any tags are applied.
      do_trim: switch to trim whitespace around the image

      img_tags: a dictionary of tags to be added to the image metadata.
       
      keep_open: by default, this savefig wrapper closes the figure after use, except if keep_open is True.

      verbose: switch for verbose output (reports file sizes before/after conversion)
    '''
    
    
    if img_format is None:
        write_file = filename
        # get the img_format from the end of the filename
        _, img_format = os.path.splitext(filename)
        if img_format is None or img_format == '':
            raise ValueError('Cannot determine file img_format to save from filename "%s"' % filename)
        
        # get rid of the . to be consistent throughout
        img_format = img_format[1:]
    else:
        if img_format.startswith('.'):
            img_format = img_format[1:]
        write_file = '%s.%s' % (filename, img_format)
        
    
    # should probably add lots of other args, or use **kwargs
    if dpi:
        plt.savefig(write_file, dpi=dpi)
    else:
        plt.savefig(write_file)
    
    if not keep_open:
        plt.close()

    if img_format == 'png':
        image_file_postproc(write_file, img_converter=img_converter, \
                                 do_trim=do_trim, verbose=verbose, img_tags=img_tags)
    else:
        raise NotImplementedError('Currently, ImageMetaTag does not support "%s" format images' % img_format)


def image_file_postproc(filename, outfile=None, img_converter=0, do_trim=False, img_tags=None, verbose=False):
    '''Image post-processing
    
    Arguments: filename   the namme of the file to process
    
    Options:
      outfile: If supplied, the processing will be applied to a new file, with this name. If not supplied, the 
               post processing will overwrite the file given by the filename.
               
      img_converter: an integer switch controlling the level of file size compression
                     0 - no compression
                     1 - light compression, from RGBA to RGB
                     2 - moderate compression, from RGBA to RGB, then to an adaptive 256 colour palette.
                     3 - heavy compression, from RGBA to RGB, then to 8-bit web standard palette.
      
      do_trim: switch to trim whitespace from the edge of the image
      
      img_tags: a dictionary of tags to be added to the image metadata
      
      verbose: switch for verbose output (reports file sizes before/after conversion)
    '''

    # usually, this is used to overwrite a file, but an outfile can be specified:
    if not outfile:
        outfile = filename
    
    st_fsize = os.path.getsize(filename)
    
    if not (img_tags is None or isinstance(img_tags, dict)):
        raise ValueError('Image tags must be supplied as a dictionary')
    
    if img_converter == 0:
        # no compression...
        # but other options may be needed:
        if (do_trim or img_tags):
            # use the image library to open the file:
            im_obj = Image.open(filename)
            if do_trim:
                # call the im_trim routiune defined above:
                im_obj = im_trim(im_obj)
            if img_tags:
                # add the tags
                im_obj = im_add_png_tags(im_obj, img_tags)
                # and save with metadata
                im_pngsave_addmeta(im_obj, outfile, optimize=True, verbose=verbose)
            else:
                # simple save
                im_obj.save(outfile, optimize=True)
                
    elif img_converter in [1, 2, 3]:
        # use the image library to open the file:
        im_obj = Image.open(filename)
        
        # call the im_trim routiune defined above:
        if do_trim:
            im_obj = im_trim(im_obj)
        
        # images start out as RGBA, strip out the alpha channel first by covnerting to RGB,
        # then you convert to the next format (that's key to keeping image quality, I think):
        if img_converter == 1:
            # this is a good quality image, but not very much smaller:
            im_obj = im_obj.convert('RGB')
        
        elif img_converter == 2:
            # second conversion to 8-bit 'P', palette mode with an adaptive palette. 
            # works well for line plots.
            im_obj = im_obj.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=256)
            
        elif img_converter == 3:
            # this is VERY strong optimisation and the result can be speckly.
            im_obj = im_obj.convert('RGB').convert('P', palette=Image.WEB)
        
        
        if img_tags:
            im_obj = im_add_png_tags(im_obj, img_tags)
            im_pngsave_addmeta(im_obj, outfile, optimize=True, verbose=verbose)
        else:
            # simple save
            im_obj.save(outfile, optimize=True)
    else:
        raise ValueError('Unavailable method for image conversion')

    # now report the file size change:
    en_fsize = os.path.getsize(outfile)
    if verbose:
        print '%s%s%s%s%s%s' % ('File: "', filename, \
                            '".\n    Starting filesize: ', st_fsize, ', final filesize: ', en_fsize)

def im_trim(im_obj):
    'Trims an image object using Python Image Library'
    # make a white background:
    backg = Image.new(im_obj.mode, im_obj.size, im_obj.getpixel((0, 0)))
    # do an image difference:
    diff = ImageChops.difference(im_obj, backg)
    # add it together
    diff = ImageChops.add(diff, diff, 1.0, -100)
    # and see what the bbox is of that...
    bbox = diff.getbbox()
    if bbox:
        # crop:
        return im_obj.crop(bbox)
    else:
        return im_obj
    
def im_pngsave_addmeta(im_obj, outfile, optimize=True, verbose=False):
    'saves an image object to a png file, adding metadata using the info tag...'
    # these can be automatically added to Image.info dict
    # they are not user-added metadata
    reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect', 'signature', \
                'date:create', 'date:modify')

    # undocumented class
    meta = PngImagePlugin.PngInfo()

    # copy metadata into new object
    for key, val in im_obj.info.iteritems():
        if key in reserved:
            pass
        elif val is None:
            if verbose:
                print 'key "%s" is set to None' % key
        else:
            meta.add_text(key, val, 0)

    # and save
    im_obj.save(outfile, "PNG", optimize=optimize, pnginfo=meta)
    
def im_add_png_tags(im_obj, png_tags):
    'adds img_tags to an image object for later saving'
    for key, val in png_tags.iteritems():
        im_obj.info[key] = val
    return im_obj

