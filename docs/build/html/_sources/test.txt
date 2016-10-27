.. ImageMetaTag documentation for test.py

ImageMetaTag - test.py
========================================

The test.py script includes tests for the main functionality of ImageMetaTag. It also acts as a demonstration of the code in action.

Running the command::

  python test.py

will create a set of plots of random data, create a number of :class:`ImageMetaTag.ImageDict` objects describing how image metadata should be presented, and write these to webpages to browse them. The images and webpages are created in a directory::
  ${HOME}/public_html/ImageMetaTagTest

The test.py script is not a part of the ImageMetaTag module, it is written to import the module and use it instead.

.. warning::

   Currently these links only work within the Met Office

The webpages it produces can be viewed here:
 * A basic page presenting the plots: http://www-nwp/~freb/ImageMetaTagTest/page.html
 * A basic page, where the metadata processing was parallelised: http://www-nwp/~freb/ImageMetaTagTest/page_para.html
 * A page where multiple images are presented at the same time: http://www-nwp/~freb/ImageMetaTagTest/page_multi.html


The test.py script can be run without re-plotting the random data by::

  python test.py --skip-plotting

As a scalability test, once the images have been produced and wepages created, the test.py script also creates a much larger :class:`ImageMetaTag.ImageDict` with 9 factorial (9! = 362880)  members. This process only mimics the metadata, it does not actually create the plots!

This test can be skipped by running the test as::

  python test.py --no-big-dict


