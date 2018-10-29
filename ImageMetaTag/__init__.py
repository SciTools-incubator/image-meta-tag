'''
ImageMetaTag is a python package built around a wrapper for
`savefig <http://matplotlib.org/api/pyplot_api.html?highlight=savefig#matplotlib.pyplot.savefig>`_
in
`matplotlib <http://matplotlib.org/>`_, which adds metadata tags to supported image
file formats.

Once the images have been tagged, it can also be used to manage an
`SQL database <https://docs.python.org/2/library/sqlite3.html>`_ of images and their
metadata. The image metadata can be used to produce an
:class:`ImageMetaTag.ImageDict` object: a structured/heirachical dictionary of dictionaries
which can be used to easily create web pages to present large numbers of images.

As the image metadata tagging process involves reading the image using the Image library,
a few common image post-processing options are included such as cropping, logo addition and
colour palette manipulation to reduce filesizes.

.. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks

(C) Crown copyright Met Office. All rights reserved.
Released under BSD 3-Clause License. See LICENSE for more details.
'''

import platform

# Set constants/properties of ImageMetaTag (before any of it is imported)
# see release_process for details on incrementing the version
__version__ = '0.7.6'
__documentation__ = 'http://scitools-incubator.github.io/image-meta-tag/build/html/'
# list fo file formats which are valid for saving metadata to:
META_IMG_FORMATS = ['png']
# and which can do image post-processing
POSTPROC_IMG_FORMATS = ['png']
# default timeout and retries for database access:
DEFAULT_DB_TIMEOUT = 6
DEFAULT_DB_ATTEMPTS = 20

# we want all of the functions in webpage and db, as a separate level
import ImageMetaTag.webpage
import ImageMetaTag.db
# but only specfic parts of savefig and img_dict:
from ImageMetaTag.savefig import savefig
from ImageMetaTag.savefig import image_file_postproc
from ImageMetaTag.img_dict import ImageDict
from ImageMetaTag.img_dict import readmeta_from_image
from ImageMetaTag.img_dict import dict_heirachy_from_list
from ImageMetaTag.img_dict import dict_split
from ImageMetaTag.img_dict import simple_dict_filter
from ImageMetaTag.img_dict import check_for_required_keys

if platform.python_version().startswith('2'):
    PY3 = False
elif platform.python_version().startswith('3'):
    PY3 = True
else:
    raise NotImplementedError('Only writtend for python2 or python3')
