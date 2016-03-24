'''
Module containing a wrapper for matplotlib.pyplot.savefig, which adds image metadata taggging
and basic image maniupulation.

.. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks
'''

import os, sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

from ImageMetaTag import db, META_IMG_FORMATS, DEFAULT_DB_TIMEOUT, DEFAULT_DB_ATTEMPTS

# image manipulations:
import Image, ImageChops
from PIL import PngImagePlugin
import numpy as np

THUMB_DEFAULT_IMG_SIZE = 150, 150
THUMB_DEFAULT_DIR_NAME = 'thumbnail'

def savefig(filename, img_format=None, img_converter=0, do_trim=False, trim_border=0,
            do_thumb=False, img_tags=None, keep_open=False, dpi=None,
            logo_file=None, logo_width=40, logo_padding=0, logo_pos=0,
            db_file=None, db_timeout=DEFAULT_DB_TIMEOUT, db_attempts=DEFAULT_DB_ATTEMPTS,
            verbose=False, ):
    '''
    Little routine to wrap over matplotlib.pyplot.savefig, to include file size optimisation and
    image tagging.

    The filesize optimisation depends on the img_converter input passes into
    :func:`ImageMetaTag.image_file_postproc`.

    Args:
    filename (can include the file extension, or that can be specified in the img_format option)

    Options:

    * img_format - file format of the image, usually without the ".". Currently only the png file \
                   img_format is supported for tagging/conversion.
    * img_tags - a dictionary of {tag_name : value} pairs to be added to the image metadata.
    * img_converter - see :func:`ImageMetaTag.image_file_postproc`.
    * do_trim - see :func:`ImageMetaTag.image_file_postproc`.
    * trim_border - see :func:`ImageMetaTag.image_file_postproc`.
    * logo_file - see :func:`ImageMetaTag.image_file_postproc`.
    * logo_width - see :func:`ImageMetaTag.image_file_postproc`.
    * logo_padding - see :func:`ImageMetaTag.image_file_postproc`.
    * logo_pos - see :func:`ImageMetaTag.image_file_postproc`.
    * do_thumb - see :func:`ImageMetaTag.image_file_postproc`.
    * keep_open - by default, this savefig wrapper closes the figure after use, except if \
                  keep_open is True.
    * verbose - switch for verbose output (reports file sizes before/after conversion)

    TODO: the logo would also be good if it could accept a list of files, widths,
    positions and paddings. That way different logos could be added to the top left and top
    right  corner, for instance.

    '''

    if img_format is None:
        write_file = filename
        # get the img_format from the end of the filename
        _, img_format = os.path.splitext(filename)
        if img_format is None or img_format == '':
            msg = 'Cannot determine file img_format to save from filename "%s"' % filename
            raise ValueError(msg)

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

    if img_format in META_IMG_FORMATS:
        use_img_tags = img_tags
    else:
        use_img_tags = None

    if verbose:
        postproc_st = datetime.now()

    if img_format == 'png':
        image_file_postproc(write_file, img_converter=img_converter, do_trim=do_trim,
                            trim_border=trim_border, logo_file=logo_file, logo_width=logo_width,
                            logo_padding=logo_padding, logo_pos=logo_pos,
                            do_thumb=do_thumb, img_tags=use_img_tags, verbose=verbose)
    else:
        msg = 'Currently, ImageMetaTag does not support "%s" format images' % img_format
        raise NotImplementedError(msg)

    if verbose:
        print 'Image post-processing took: %s' %(str(datetime.now() - postproc_st))


    # now write to the database, if it is specifed:
    if not (db_file is None or img_tags is None):
        if verbose:
            db_st = datetime.now()
        wrote_db = False
        n_tries = 1
        while not wrote_db and n_tries <= db_attempts:
            try:
                db.write_img_to_dbfile(db_file, filename, img_tags, timeout=db_timeout)
                wrote_db = True
            except sqlite3.OperationalError as OpErr:
                print '%s database timeout for image "%s", writing to file "%s", %s s' \
                            % (db.dt_now_str(), db_file, write_file, n_tries * db_timeout)
                n_tries += 1
            except:
                raise
        if n_tries > db_attempts:
            raise sqlite3.OperationalError(OpErr.message)
        if verbose:
            print 'Database write took: %s' %(str(datetime.now() - db_st))

def image_file_postproc(filename, outfile=None, img_converter=0, do_trim=False, trim_border=0,
                        logo_file=None, logo_width=40, logo_padding=0, logo_pos=0,
                        do_thumb=False, img_tags=None, verbose=False):
    '''Image post-processing for :func:`ImageMetaTag.savefig`.

    Arguments: filename the name of the image file to process

    Options:

    * outfile - If supplied, the processing will be applied to a new file, with this name. \
                If not supplied, the post processing will overwrite the file given input file.
    * img_converter - an integer switch controlling the level of file size compression
                    * 0 - no compression
                    * 1 - light compression, from RGBA to RGB
                    * 2 - moderate compression, from RGBA to RGB, then to an adaptive 256 colour \
                          palette.
                    * 3 - heavy compression, from RGBA to RGB, then to 8-bit web standard palette.
    * do_trim - switch to trim whitespace from the edge of the image
    * trim_border - if do_trim then this can be used to define an integer number of pixels as a \
                    border around the trim.
    * logo_file - a file to use as a logo, to be added to the image
    * logo_width - the desired width of the logo, in pixels. If the supplied image file is not \
                   the right size, it will be resized using a method that applies filters and \
                   antialiasing that works well for shrinking images with text to a much \
                   smaller size. The aspect ratio of the logo image is always maintained. \
                   Defaults to 40 pixels.
    * logo_padding - a number of pixels to pad around the logo (default to zero)
    * logo_pos - corner position of the logo (following pyplot.legend, but for corners) \
               * 0: 'best' in this context will be upper left (default)
               * TODO: 1: 'upper right'
               * 2: 'upper left'
               * TODO: 3: 'lower left'
               * TODO: 4: 'lower right'
    * do_thumb - switch to produce default sized thumbnail, or integer/tuple to define the \
                 maximum size in pixels
    * img_tags: a dictionary of tags to be added to the image metadata
    * verbose: switch for verbose output (reports file sizes before/after conversion)
    '''

    # usually, this is used to overwrite a file, but an outfile can be specified:
    if not outfile:
        outfile = filename

    if verbose:
        st_fsize = os.path.getsize(filename)

    if not (img_tags is None or isinstance(img_tags, dict)):
        raise ValueError('Image tags must be supplied as a dictionary')

    if not img_converter in range(4):
        raise ValueError('Unavailable method for image conversion')

    # do_thumb should equate to integer type or be a tuple of integers
    #
    # this test is taking advantage of the isinstance(do_thumb, tutple) being true before testing
    # the contents of do_thumb.
    # Also that as a bool, do_thumb also passes  isinstance(do_thumb, int).
    if not isinstance(do_thumb, int) or (isinstance(do_thumb, tuple)
                                         and isinstance(do_thumb[0], int)
                                         and isinstance(do_thumb[1], int)):
        raise ValueError('Invalid thumbnail size')

    # do we do any image modification at all?
    modify = do_trim or do_thumb or img_tags or img_converter > 0 or logo_file is not None

    if modify:
        # use the image library to open the file:
        im_obj = Image.open(filename)

    if do_trim:
        # call the _im_trim routine defined above:
        im_obj = _im_trim(im_obj, border=trim_border)

    if logo_file is not None:
        im_obj = _im_logo(im_obj, logo_file, logo_width, logo_padding, logo_pos)

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

    if do_thumb:
        # set a default thumbnail directory name and determine relative paths
        thumb_dir_name = THUMB_DEFAULT_DIR_NAME
        thumb_directory = os.path.join(os.path.split(outfile)[0], thumb_dir_name)
        thumb_full_path = os.path.join(thumb_directory, os.path.split(outfile)[1])

        # create thumbnail directory if one does not exist
        if not os.path.isdir(thumb_directory):
            os.mkdir(thumb_directory)

        # set to default thumbnail size if no size specified
        if do_thumb is True:
            do_thumb = THUMB_DEFAULT_IMG_SIZE

        # check input
        elif not isinstance(do_thumb, tuple):
            do_thumb = (do_thumb, do_thumb)

        # create the thumbnail
        im_thumb = im_obj.copy()
        im_thumb.thumbnail(do_thumb, Image.ANTIALIAS)

        if img_tags:
            # add the tags
            im_thumb = _im_add_png_tags(im_thumb, img_tags)
            # and save with metadata
            _im_pngsave_addmeta(im_thumb, thumb_full_path,
                                optimize=True, verbose=verbose)
            # set a thumbnail directory tag for the main image
            img_tags.update({'thumbnail directory' : thumb_dir_name})
        else:
            # simple save
            im_thumb.save(thumb_full_path, optimize=True)

    if img_tags:
        # add the tags
        im_obj = _im_add_png_tags(im_obj, img_tags)
        # and save with metadata
        _im_pngsave_addmeta(im_obj, outfile, optimize=True, verbose=verbose)
    elif modify:
        # simple save
        im_obj.save(outfile, optimize=True)

    if verbose:
        # now report the file size change:
        en_fsize = os.path.getsize(outfile)
        print 'File: "%s". Size: %s, to %s bytes' % (filename, st_fsize, en_fsize)

def _im_trim(im_obj, border=0):
    'Trims an image object using Python Image Library'
    if not isinstance(border, int):
        msg = 'Input border must be an int, but is %s, %s instead' %(border, type(border))
        raise ValueError(msg)
    # make a white background:
    backg = Image.new(im_obj.mode, im_obj.size, im_obj.getpixel((0, 0)))
    # do an image difference:
    diff = ImageChops.difference(im_obj, backg)
    # add it together
    diff = ImageChops.add(diff, diff, 1.0, -100)
    # and see what the bbox is of that...
    bbox = diff.getbbox()

    if border != 0:
        border_bbox = [-border, -border, border, border]
        # now apply that trim:
        bbox_tr = [x+y for x, y in zip(bbox, border_bbox)]

        # bbox defines the first corner as top+left, then the second corner as bottom+right
        # (not the bottom left corner, and the width, height from there)
        if bbox_tr[0] < 0:
            bbox_tr[0] = 0
        if bbox_tr[1] < 0:
            bbox_tr[1] = 0
        if bbox_tr[2] > im_obj.size[0]:
            bbox_tr[2] = im_obj.size[0]
        if bbox_tr[3] > im_obj.size[1]:
            bbox_tr[3] = im_obj.size[1]
        # now check to see if that's actually foing to do anything:
        if bbox_tr == [0, 0, im_obj.size[0], im_obj.size[1]]:
            bbox = None
        else:
            bbox = bbox_tr

    if bbox:
        # crop:
        return im_obj.crop(bbox)
    else:
        return im_obj

def _im_logo(im_obj, logo_file, logo_width, logo_padding, logo_pos):
    'adds a logo to the required corner of an image object (usually after an im_trim)'

    # load in the logo file image:
    logo_obj = Image.open(logo_file)
    # rescale to the new width and height:
    if logo_width != logo_obj.size[0]:
        logo_height = int(logo_obj.size[1] * float(logo_width) / logo_obj.size[0])
        res_logo_obj = _img_premult_resize(logo_obj, size=(logo_width, logo_height))
    else:
        res_logo_obj = logo_obj

    # TODO: this is written for putting a logo in the top-left corner, but could be extended:
    if logo_pos in [0, 2]:

        # now pull out a sub image from the main image, that's just where the logo would go,
        # it it were this is the size we want to have blank, to put the logo, including padding:
        req_logo_size = [x + 2*logo_padding for x in res_logo_obj.size]

        corner_obj = im_obj.crop((0, 0, req_logo_size[0], req_logo_size[1]))
        #
        # now get a bounding box as though we were trimming this image:
        backg = Image.new(corner_obj.mode, corner_obj.size, corner_obj.getpixel((0, 0)))
        # do an image difference:
        diff = ImageChops.difference(corner_obj, backg)
        # add it together
        diff = ImageChops.add(diff, diff, 1.0, -100)
        # and see what the bbox is of that...
        bbox = diff.getbbox()

#        # get the offset in x and y:
#        if bbox is None:
#            # the corner object is empty so no need to offset:
#            offsets = (0,0)
#        else:
#            offsets = (req_logo_size[0] - bbox[0], req_logo_size[1] - bbox[1])
#        # but you only ever need to offset in one direction (the shortest one):
#        offset = min(offsets)
#        offset_ind = offsets.index(offset)

        # as this is the top left corner of a plot, the logo should be offset only
        # in x (so the title is still at the top)
        if bbox is None:
            # the corner object is empty so no need to offset:
            offset = 0
        else:
            offset = req_logo_size[0] - bbox[0]
        offset_ind = 0


        # now put that together to make an image:

        # create the blank image:
        new_size = list(im_obj.size)
        new_size[offset_ind] += offset
        new_obj = Image.new(im_obj.mode, new_size, im_obj.getpixel((0, 0)))

        # now put the main image into it, offset:
        if offset_ind == 0:
            offsets = (offset, 0)
        else:
            offsets = (0, offset)
        new_obj.paste(im_obj, offsets)
        # and put the rescaled logo onto it too, in the right place:
        new_obj.paste(res_logo_obj, (logo_padding, logo_padding))

    else:
        msg = 'logo positions other than 0 and 2 (both top left) have not been implemented yet'
        raise NotImplementedError(msg)

    return new_obj

def _im_add_png_tags(im_obj, png_tags):
    'adds img_tags to an image object for later saving'
    for key, val in png_tags.iteritems():
        im_obj.info[key] = val
    return im_obj

def _im_pngsave_addmeta(im_obj, outfile, optimize=True, verbose=False):
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

def _img_premult_resize(img_obj, size=None):
    'does image pre-processing before a strong resize, to get rid of halo effects'

    if size is None:
        size = (40, 40)

    img_obj = img_obj.convert('RGBA')
    premult = np.fromstring(img_obj.tostring(), dtype=np.uint8)
    alpha_layer = premult[3::4] / 255.0
    premult[0::4] *= alpha_layer
    premult[1::4] *= alpha_layer
    premult[2::4] *= alpha_layer
    new_img_obj = Image.fromstring("RGBA", img_obj.size, premult.tostring())

    #new_img_obj = new_img_obj.filter(ImageFilter.SMOOTH)
    res_img_obj = new_img_obj.resize(size, Image.ANTIALIAS)

    return res_img_obj

