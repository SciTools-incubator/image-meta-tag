'''
Produces a set of test plots using matplotlib, with just random data.

Each plot is tagged with appropriate metadata, and an ImageDict produced which describes
them and creates a web page.
'''


import os, errno

import numpy as np
import matplotlib.pyplot as plt

import ImageMetaTag as imt

def mkdir_p(path):
    """
    Routine to mimic mkdir -p behaviour
    Note: os.makedirs throws up error if directory already exists
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else: raise


def __main__():
    
    imt_verbose = True
    
    n_random_data = 5
    random_data = []
    # simulate rolling 2 6 sided dice:
    for i_rand in range(n_random_data):
        n_rolls = 6**(i_rand+1)
        random_data.append(np.random.random_integers(1, 6, n_rolls) + np.random.random_integers(1, 6, n_rolls) )
    
    
    img_savedir = '%s/public_html/ImageMetaTagTest' % os.getenv('HOME')
    mkdir_p(img_savedir)
    
    compression_levels = [0, 1, 2, 3]
    trims = [True, False]
 
    
    images_and_tags = {}
    
    # now plot the random data in some different ways, tagging the image as we go:
    for i_rand in range(n_random_data):
        n_rolls = 6**(i_rand+1)
        
        plt.plot(random_data[i_rand], linestyle=':', marker='x')
        plt.ylim([1, 12])
        plt.title('Sum of two random integers between 1 and 6')
        
        outfile = '%s/rolls_%s' % (img_savedir, n_rolls)
        plt.savefig(outfile+'.png')
 
        # save the figure, using different image-meta-tag options
        # and tag the images.
        for trim in trims:
            for compression in compression_levels:
                outfile = '%s/rolls_imt_%s_compression_%s' % (img_savedir, n_rolls, compression)
                if trim:
                    outfile += '_trim'
                    trim_str = 'Image trimmed'
                else:
                    trim_str = 'Image untrimmed'
                img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                            'image compression': 'Compression option %s' % compression,
                            'image trim': trim_str}
                imt.savefig(outfile+'.png', 
                            do_trim=trim, 
                            img_converter=compression, 
                            img_tags=img_tags,
                            keep_open=True, 
                            verbose=imt_verbose)
                images_and_tags[outfile] = img_tags
        plt.close()
        
        outfile = '%s/dist_%s' % (img_savedir, n_rolls)
        _count, _bins, _ignored = plt.hist(random_data[i_rand], [x+0.5 for x in range(13)], normed=True)
        plt.xlim([1, 13])
        plt.title('Distribution of %s random integers between 1 and 6' % n_rolls )
        plt.savefig(outfile+'.png')
        
        for trim in trims:
            for compression in compression_levels:
                outfile = '%s/dist_imt_%s_compression_%s' % (img_savedir, n_rolls, compression)
                if trim:
                    outfile += '_trim'
                    trim_str = 'Image trimmed'
                else:
                    trim_str = 'Image untrimmed'
                img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                            'image compression': 'Compression option %s' % compression,
                            'image trim': trim_str}
                imt.savefig(outfile+'.png', 
                            do_trim=trim, 
                            img_converter=compression, 
                            img_tags=img_tags,
                            keep_open=True, 
                            verbose=imt_verbose)
                images_and_tags[outfile] = img_tags
        plt.close()
        
        
    print images_and_tags
    
    # now test that the meta tags can be re-read in from the file on disk:
    for img_file, saved_tags in images_and_tags.items():
        (read_ok, img_tags) = imt.img_dict.readmeta_from_image(img_file)
        print img_tags
    
if __name__ == '__main__':
    __main__()