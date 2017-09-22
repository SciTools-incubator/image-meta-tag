.. ImageMetaTag documentation for simplest_img_dict.py

ImageMetaTag - simplest_img_dict.py
========================================

While the code in test.py aims to test as much of the ImageMetaTag functionality as possible, this routine aims to show the simplest possible code that keeps 'best practice' to use an ImageMetaTag database of metadata to produce a webpage.

.. code-block:: python
    
    '''
    While the code in test.py aims to test as much of the ImageMetaTag functionality as possible,
    this routine aims to show the simplest possible code that keeps 'best practice' to use an
    ImageMetaTag database of metadata to produce a webpage.
    
    .. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks
    '''
    
    # minimal set of imports:
    import datetime
    
    # import ImageMetaTag:
    import ImageMetaTag as imt
    
    # we are going to use just a couple of things from the test.py routine.
    from test import get_webdir, define_imt_db, DATE_FORMAT_WWW
    
    def __main__():
        # define the web page directory and image database
	# Any real application of an ImageDict web page would need to
	# define the locations of the web page and database for its own
	# requirements.
	# In this case, we are using the same functions in test, to be sure that
	# they are consistent.
        webdir = get_webdir()
        imt_db = define_imt_db()
    
        # these are the image tags that are present in the metadata, and
        # the sort order we want to present them with on a web page:
        img_tags = ['plot type', 'number of rolls', 'plot color',
                    'image trim', 'border', 'image compression']
        # and how those tags are to be sorted:
        sort_methods = ['sort', 'numeric', 'reverse_sort', 'sort', 'reverse_numeric', 'sort']
    
        # Now load in the database:
        tag_strings = []
        img_list, images_and_tags = imt.db.read(imt_db, required_tags=img_tags,
                                                tag_strings=tag_strings)
        # we have supplied the database read with the image tags we expect, and an empty list of values
        # so that we can construct what is returned (and therefore the ImageDict) in a memory
        # efficient way.
    
        # the img_list is a list of the images in the databse file:
        print img_list
    
        # now assemble the ImageDict in the simple way. See test.py for parallel versions etc.
        img_dict = None
        for img_file, img_info in images_and_tags.iteritems():
            # make a temporary ordered dictionary for this image:
            tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, img_tags)
            if not img_dict:
                # turn it into an ImageDict
                img_dict = imt.ImageDict(tmp_dict)
            else:
                # append this tmp_dict to the ImageDict
                img_dict.append(imt.ImageDict(tmp_dict))
        # printing the img_dict will show it's heirachy (but is a lot of text):
        print img_dict
        # now sort the keys of each level of the ImageDict according to the sort_method
        img_dict.sort_keys(sort_methods)
    
        # now write a webpage:
        page_filename = '{}/simple.html'.format(webdir)
        # the title:
        page_title = 'Simple ImageMetaTag wegbpage'
        # html content to go at the top of the page:
        webpage_preamble = '<h3>This is the simplest page ImageMetaTag can produce</h3>'
        # and some html content at the bottom:
        webpage_postamble = '<i>Page produced {}</i>'.format(datetime.datetime.now().strftime(DATE_FORMAT_WWW))
        imt.webpage.write_full_page(img_dict, page_filename, page_title,
                                    preamble=webpage_preamble,
                                    postamble=webpage_postamble)
    
        # and sign off as completed:
        print 'completed, using ImageMetaTag at {}'.format(imt.__path__[0])
    
    if __name__ == '__main__':
        __main__()
