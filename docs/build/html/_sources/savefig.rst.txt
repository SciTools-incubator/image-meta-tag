.. ImageMetaTag documentation for ImageMetaTag.savefig

ImageMetaTag.savefig
========================================

.. automodule:noindex: ImageMetaTag.savefig

The savefig wrapper
-------------------
The only function that is usaully needed from this module is savefig wrapper iteself:

.. autofunction:: ImageMetaTag.savefig

Recommended file structure
--------------------------
In order to produce a working web page in the easiest and quickest manner it is advisable to save the images in a structure along the lines of:

* A top level directory, in a location which will be served up by a web server. e.g. in directory in ${HOME}/public_html/ or ${HOME}/Public/.

  * The image metadata database files should be saved to this directory.
  * The images themselves should be saved in subdirectories within this directory.

    * When saving an image with :func:`ImageMetaTag.savefig` and saving metadata to a database, then it will store the file paths of the images as relative paths to the database files.
    * If you need to save these files elsewhere, due to storage limitations, then create a symbolic link to that location from the top level directory. When you save the files with :func:`ImageMetaTag.savefig` use the symbolic link in the path, so the database files still contains relative paths. The storage location will need to be accessible by the web-server which will provide access to the web pages.
    * Use the paths relative to the databse file to create an :class:`ImageMetaTag.ImageDict` class with the metadata.

  * Once the :class:`ImageMetaTag.ImageDict` has been created, then the web pages can be created in the top level, web accessible, directory.
  * By keeping the **database and web pages in the same location**, and **storing relative paths** in the :class:`ImageMetaTag.ImageDict` then the paths to the images will also be correct in the web pages without having to do any complex path manipulation.


Other functions
---------------
The image_file_postproc function could be used to process pre-created images:

.. autofunction:: ImageMetaTag.image_file_postproc


