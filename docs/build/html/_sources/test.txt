.. ImageMetaTag documentation for test.py

ImageMetaTag - test.py
========================================

The test.py script includes tests for the main functionality of ImageMetaTag. It also acts as a demonstration of the code in action on a set of very simple example plots of random data.

Running the command::

  python test.py

will create a set of plots of random data, create a number of :class:`ImageMetaTag.ImageDict` objects describing how image metadata should be presented, and write these to webpages to browse them. The images and webpages are created in a directory::
  ${HOME}/public_html/ImageMetaTagTest

The test.py script is not a part of the ImageMetaTag module, it is written to import the module and use it instead.

The webpages it produces can be viewed here:
 * A basic page presenting the plots: http://gws-access.ceda.ac.uk/public/mo_forecasts/test/ImageMetaTagTest/page.html
 * A basic page, where the metadata processing was parallelised: http://gws-access.ceda.ac.uk/public/mo_forecasts/test/ImageMetaTagTest/page_para.html
 * A page where multiple images are presented at the same time: http://gws-access.ceda.ac.uk/public/mo_forecasts/test/ImageMetaTagTest/page_multi.html

The test.py script can be run without re-plotting the random data by::

  python test.py --skip-plotting

As a scalability test, once the images have been produced and wepages created, the test.py script also creates a moderately large :class:`ImageMetaTag.ImageDict` with 9 factorial (9! = 362880)  members. This process only mimics the metadata, it does not actually create the plots! It results in a web page which is deliberately empty: http://gws-access.ceda.ac.uk/public/mo_forecasts/test/ImageMetaTagTest/biggus_pageus.html 

This test can be skipped by running the test as::

  python test.py --no-big-dict

  
