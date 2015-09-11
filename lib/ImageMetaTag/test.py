'''
Produces a set of test plots using matplotlib, with just random data.

Each plot is tagged with appropriate metadata, and an ImageDict produced which describes
them and creates a web page.

@author: Malcolm.E.Brooks@metoffice.gov.uk
'''

from datetime import datetime, timedelta
DATE_START = datetime.now()
# and a format to print to stdour:
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

import os, errno, pdb

import numpy as np
import matplotlib.pyplot as plt
import cPickle as pickle
from multiprocessing import Pool

# Now, import ImageMetaTag to do things:
import ImageMetaTag as imt

def make_random_data(n_random_data):
    'generates some data sets of random data, simulating rolling 2 D6 a number of times.'
    random_data = []
    # simulate rolling 2 6 sided dice:
    for i_rand in range(n_random_data):
        n_rolls = 6**(i_rand+1)
        random_data.append(np.random.random_integers(1, 6, n_rolls) + np.random.random_integers(1, 6, n_rolls) )
    return random_data

def plot_random_data(random_data, i_rand, plot_col, col_name, trims, compression_levels, img_savedir, img_format):
    'plots a set of random data'

    imt_verbose = True
    images_and_tags = {}
    
    n_rolls = 6**(i_rand+1)
    plt.plot(random_data[i_rand], color=plot_col, linestyle=':', marker='x')
    plt.ylim([1, 12])
    plt.title('Sum of two random integers between 1 and 6')
    
    outfile = '%s/rolls_%s_%s.%s' % (img_savedir, n_rolls, plot_col, img_format)
    plt.savefig(outfile+'.png')
    
    # save the figure, using different image-meta-tag options
    # and tag the images.
    for trim in trims:
        for compression in compression_levels:
            outfile = '%s/rolls_imt_%s_%s_compression_%s' % (img_savedir, n_rolls, plot_col, compression)
            if trim:
                outfile += '_trim'
                trim_str = 'Image trimmed'
            else:
                trim_str = 'Image untrimmed'
            outfile += '.%s' % img_format
            img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                        'plot type': 'Line plots',
                        'image compression': 'Compression option %s' % compression,
                        'image trim': trim_str, 
                        'plot color': col_name}
            imt.savefig(outfile, do_trim=trim, 
                        img_converter=compression, 
                        img_tags=img_tags,
                        keep_open=True, 
                        verbose=imt_verbose)
            # now store those tags
            images_and_tags[outfile] = img_tags
            # and check they are the same as those that come from reading the image metatadata from disk:
            check_img_tags(outfile, img_tags)
    
    plt.close()
    
    
    outfile = '%s/dist_%s_%s' % (img_savedir, n_rolls, plot_col)
    _count, _bins, _ignored = plt.hist(random_data[i_rand], [x+0.5 for x in range(13)], color=plot_col, normed=True)
    plt.xlim([1, 13])
    plt.title('Distribution of %s random integers between 1 and 6' % n_rolls )
    plt.savefig(outfile+'.png')
    
    for trim in trims:
        for compression in compression_levels:
            outfile = '%s/dist_imt_%s_%s_compression_%s' % (img_savedir, n_rolls, plot_col, compression)
            if trim:
                outfile += '_trim'
                trim_str = 'Image trimmed'
            else:
                trim_str = 'Image untrimmed'
            outfile += '.%s' % img_format
            img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                        'plot type': 'Histogram',
                        'image compression': 'Compression option %s' % compression,
                        'image trim': trim_str, 
                        'plot color': col_name}
            imt.savefig(outfile, do_trim=trim, 
                        img_converter=compression, 
                        img_tags=img_tags,
                        keep_open=True, 
                        verbose=imt_verbose)
            # log tags:
            images_and_tags[outfile] = img_tags
            # and check:
            check_img_tags(outfile, img_tags)
    plt.close()
    
    return images_and_tags

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

def check_img_tags(img_file, in_tags):
    'raises an error if the tags read from a file do not match those written to it, or are unreadable'

    (read_ok, read_tags) = imt.readmeta_from_image(img_file)

    if not read_ok:
        raise ValueError('Unable to read image tags for file "%s"' % img_file)

    if in_tags != read_tags:
        msg = 'Image metadata tags read from file "%s" do not match the expected tags.\n' % img_file
        msg += '  Input tags:\n'
        for key, val in in_tags.items():
            msg += '     "%s" : "%s"\n' % (key, val)
        msg += '  Tags read from file:\n'
        for key, val in in_tags.items():
            msg += '     "%s" : "%s"\n' % (key, val)
       
        raise ValueError(msg)
    
def define_img_dict_in_tuple(in_tuple):
    '''
    A wrapper that defines an ImageDict from a dictionary of images and metadata.
    The input is a tuple so it can be parallelised.
    '''
    
    sub_dict = in_tuple[0]
    tag_order = in_tuple[1]
    img_savedir = in_tuple[2]
    
    img_dict = None
    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step,
    # which I might include below:
    for img_file, img_info in sub_dict.iteritems():
        relative_path = img_file[len(img_savedir)+1:]
        tmp_dict = imt.dict_heirachy_from_list(img_info, relative_path, tag_order)
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict)
        else:
            img_dict.append(imt.ImageDict(tmp_dict))

    return img_dict
     
def __main__():
    
    date_now_str = DATE_START.strftime(DATE_FORMAT)
    
    always_make_plots = False
    
    n_random_data = 5
    random_data = make_random_data(n_random_data)
    
    img_savedir = '%s/public_html/ImageMetaTagTest' % os.getenv('HOME')
    mkdir_p(img_savedir)
    
    compression_levels = [0, 1, 2, 3]
    trims = [True, False]
 
    # colours to plot with, and the names we want in the metadata/webpage
    colours = [('r', 'Plotted in Red'), 
               ('b', 'Plotted in Blue'), 
               ('k', 'Plotted in Black'), 
               ('g', 'Plotted in Green')]
 
    img_format = 'png'
    
    # this defines the order of the different tags in the ImageDict, and so how they are displayed on the webpage:
    tag_order = ['number of rolls', 'plot type', 'plot color', 'image trim', 'image compression']
    sort_methods = ['numeric', 'sort', 'sort', 'sort', 'sort']
    
    images_and_tags = {} 
    
    metadata_pickle = '%s/meta.p' % img_savedir
    if always_make_plots or not os.path.isfile(metadata_pickle):
        # now plot the random data in some different ways, tagging the image as we go:
        for i_rand in range(n_random_data):
            for (plot_col, col_name) in colours:
                new_imgs_tags = plot_random_data(random_data, i_rand, plot_col, col_name, trims, compression_levels, img_savedir, img_format)
                # now stick the new img ingo into the main dict:
                for img_file, img_info in new_imgs_tags.iteritems():
                    images_and_tags[img_file] = img_info
        
        date_end_plotting = datetime.now()
        message = 'Started at %s, completed plotting at %s, taking %s' % (date_now_str, \
                                                                          date_end_plotting.strftime(DATE_FORMAT), \
                                                                          (date_end_plotting - DATE_START))
        print message
        with open(metadata_pickle, "wb") as open_pickle:
            pickle.dump( images_and_tags, open_pickle)
        
    else:
        # load the metadata from the pickle
        print 'loading metadata from %s' % metadata_pickle
        with open(metadata_pickle, "rb") as open_pickle:
            images_and_tags = pickle.load(open_pickle)

    img_dict = None
    
    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step,
    # which I might include below:
    for img_file, img_info in images_and_tags.iteritems():
        relative_path = img_file[len(img_savedir)+1:]
        tmp_dict = imt.dict_heirachy_from_list(img_info, relative_path, tag_order)
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict)
        else:
            img_dict.append(imt.ImageDict(tmp_dict))

    
    # this test the same thing, but created in parallel. This isn't needed for a small 
    # set of plots like this example, but the code appears to scale well.
    # (within the Met Office, this code is used to produce internal web pages with 200,000+ images).
    n_proc = 2
    subdict_gen = imt.dict_split(images_and_tags, n_split=n_proc, extra_opts=(tag_order, img_savedir) )
    if n_proc == 1:
        # much easier to debug when not using the parallel calls:
        pool_out = []
        for in_tuple in subdict_gen:
            # now run the web_dir_process_images, and append the output to pool_out 
            pool_out.append( define_img_dict_in_tuple(in_tuple) )
    else:
        # now in parallel:
        proc_pool = Pool(n_proc)
        pool_out = proc_pool.map( define_img_dict_in_tuple, subdict_gen )
        proc_pool.close()
        proc_pool.join()
        
    # now stitch the parallel image dict back together:
    img_dict_para = pool_out[0]
    for i_dict in range(1, len(pool_out)): 
        img_dict_para.append(pool_out[i_dict])
    
    # sort the keys:
    img_dict.sort_keys(sort_methods)
    img_dict_para.sort_keys(sort_methods)
    
    # now these should be the same, on a print:
    print img_dict,
    print img_dict_para
    
    # now create a web page for each of them:
    out_page = '%s/page.html' % img_savedir
    out_page_para = '%s/page_para.html' % img_savedir
    
    imt.webpage.write_full_page(img_dict, out_page, 'Test ImageDict webpage', verbose=True, internal=True)
    imt.webpage.write_full_page(img_dict, out_page_para, 'Test ImageDict webpage (Parallel version)', verbose=True, internal=True)

    
if __name__ == '__main__':
    __main__()