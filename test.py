'''
Produces a set of test plots using matplotlib, with just random data.

Each plot is tagged with appropriate metadata, and an ImageDict produced which describes
them and creates a web page.

.. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks
'''

from datetime import datetime
DATE_START = datetime.now()
# and a format to print to stdour:
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

import os, shutil, sys, errno, argparse, copy, random, pdb

import numpy as np
import matplotlib.pyplot as plt
import cPickle as pickle
from multiprocessing import Pool

# make sure test is using the version of ImageMetaTag being tested:
# (this would normally be added already, by installation, but for testing, we
#  need to be testing the version we are making changes too!)
sys.path.insert(0, os.sep.join(os.path.abspath(sys.argv[0]).split(os.sep)[0:-1]) + '/lib')

LOGO_FILE = os.sep.join(os.path.abspath(sys.argv[0]).split(os.sep)[0:-1]) + '/logo.png'
if not os.path.isfile(LOGO_FILE):
    raise ValueError('No logo file found at: %s' % LOGO_FILE)
LOGO_SIZE = 60
LOGO_PADDING = 5

# Now, import ImageMetaTag to do things:
import ImageMetaTag as imt

def get_webdir():
    'Works out the location to use as webdir'

    home = os.getenv('HOME')
    webdir = None

    dirs_to_check = ['%s/public_html' % home, '%s/Public' % home]
    for check_dir in dirs_to_check:
        if os.path.isdir(check_dir):
            webdir = '%s/ImageMetaTagTest' % check_dir
            break
    if not webdir:
        raise ValueError('Cannot find appropriate web dir from: %s' % dirs_to_check)

    # make it if it doesn't exist:
    if not os.path.isdir(webdir):
        mkdir_p(webdir)

    return webdir

def get_user_and_email():
    '''
    guesses the users email address from /etc/aliases.
    This is an example of the sort of traceability information would be
    a very common tag to add to images.
    '''
    username = os.getenv('USER')
    user_email = None
    alias_file = '/etc/aliases'
    if os.path.isfile(alias_file):
        with open(alias_file, 'r') as open_file:
            for line in open_file:
                if line.startswith(username):
                    user_email = line.split()[-1]
                    break

    user_and_email = 'user: %s' % username
    if user_email:
        user_and_email += ', email: %s' % user_email
    return user_and_email

def make_random_data(n_random_data):
    'generates some data sets of random data, simulating rolling 2 D6 a number of times.'
    random_data = []
    # simulate rolling 2 6 sided dice:
    for i_rand in range(n_random_data):
        if i_rand < 6:
            n_rolls = 6 ** (i_rand + 1)
        else:
            pdb.set_trace()
            n_rolls = 6 ** (6) + 2 ** (i_rand + 1)
        random_data.append(np.random.random_integers(1, 6, n_rolls) + \
                           np.random.random_integers(1, 6, n_rolls))
    return random_data

def plot_random_data(random_data, i_rand, plot_col, col_name, trims, borders,
                     compression_levels, img_savedir, img_format, plot_owner,
                     imt_db):
    'plots a set of random data'

    # to tag the images with the routine that created it:
    this_routine = 'ImageMetaTag module: lib/ImageMetaTag/test.py'

    imt_verbose = True
    images_and_tags = {}

    db_timeout = 5

    n_rolls = 6 ** (i_rand + 1)
    plt.plot(random_data[i_rand], color=plot_col, linestyle=':', marker='x')
    plt.ylim([1, 12])

    if plot_col == 'r':
        plt.title('Sum of two random integers between 1 and 6, with an extremely long title.\n')
    else:
        plt.title('Sum of two random integers between 1 and 6\n')


    # plot individual rolls:
    rolls_savedir = '%s/rolls' % img_savedir
    mkdir_p(rolls_savedir)
    outfile = '%s/%s_%s.%s' % (rolls_savedir, n_rolls, plot_col, img_format)
    plt.savefig(outfile)

    # save the figure, using different image-meta-tag options
    # and tag the images.
    for trim in trims:
        if trim:
            these_borders = borders
        else:
            these_borders = [0]
        for border in these_borders:
            for compression in compression_levels:
                outfile = '%s/imt_%s_%s_compression_%s' \
                        % (rolls_savedir, n_rolls, plot_col, compression)
                if trim:
                    outfile += '_trim_b%s' % border
                    trim_str = 'Image trimmed'
                else:
                    trim_str = 'Image untrimmed'
                outfile += '.%s' % img_format
                # image tags for the web page:
                img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                            'plot type': 'Line plots',
                            'image compression': 'Compression option %s' % compression,
                            'image trim': trim_str,
                            'border': '%s pixels' % border,
                            'plot color': col_name}

                # and other, more general tags showing the sort of thing that might be useful:
                img_tags['data source'] = 'Some random data'
                img_tags['plot owner'] = plot_owner
                img_tags['plot created by'] = this_routine
                img_tags['ImageMetaTag version'] = imt.__version__

                imt.savefig(outfile, do_trim=trim, trim_border=border, do_thumb=True,
                            img_converter=compression,
                            img_tags=img_tags,
                            keep_open=True,
                            verbose=imt_verbose,
                            db_file=imt_db, db_timeout=db_timeout,
                            logo_file=LOGO_FILE, logo_width=LOGO_SIZE, logo_padding=LOGO_PADDING)

                # now store those tags
                images_and_tags[outfile] = img_tags
                # and check they are the same as those that come from reading
                # the image metatadata from disk:
                check_img_tags(outfile, img_tags)

    plt.close()

    # now plot distributions:
    dist_savedir = '%s/dists' % img_savedir
    mkdir_p(dist_savedir)
    outfile = '%s/%s_%s.%s' % (dist_savedir, n_rolls, plot_col, img_format)
    _count, _bins, _ignored = plt.hist(random_data[i_rand],
                                       [x + 0.5 for x in range(13)],
                                       color=plot_col, normed=True)
    plt.xlim([1, 13])
    plt.title('Distribution of %s random integers between 1 and 6\n' % n_rolls)
    plt.savefig(outfile)

    for trim in trims:
        if trim:
            these_borders = borders
        else:
            these_borders = [0]
        for border in these_borders:
            for compression in compression_levels:
                outfile = '%s/imt_%s_%s_compression_%s' \
                        % (dist_savedir, n_rolls, plot_col, compression)
                if trim:
                    outfile += '_trim_b%s' % border
                    trim_str = 'Image trimmed'
                else:
                    trim_str = 'Image untrimmed'
                outfile += '.%s' % img_format
                # tags to drive web page:
                img_tags = {'number of rolls': '%s simulated rolls' % n_rolls,
                            'plot type': 'Histogram',
                            'image compression': 'Compression option %s' % compression,
                            'image trim': trim_str,
                            'border': '%s pixels' % border,
                            'plot color': col_name}
                # again, more general tags:
                img_tags['data source'] = 'Some random data'
                img_tags['plot owner'] = plot_owner
                img_tags['plot created by'] = this_routine
                img_tags['ImageMetaTag version'] = imt.__version__

                imt.savefig(outfile, do_trim=trim, trim_border=border, do_thumb=True,
                            img_converter=compression,
                            img_tags=img_tags,
                            keep_open=True,
                            verbose=imt_verbose,
                            db_file=imt_db, db_timeout=db_timeout,
                            logo_file=LOGO_FILE, logo_width=LOGO_SIZE, logo_padding=LOGO_PADDING)
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

def print_simple_timer(dt_start, dt_end, label):
    'prints out a simple timer message'
    dt_st_str = dt_start.strftime(DATE_FORMAT)
    dt_en_str = dt_end.strftime(DATE_FORMAT)
    message = '%s: started at %s, completed at %s, taking %s' \
                % (label, dt_st_str, dt_en_str, (dt_end - dt_start))
    print message

def check_img_tags(img_file, in_tags):
    '''
    raises an error if the tags read from a file do not
    match those written to it, or are unreadable
    '''
    (read_ok, read_tags) = imt.readmeta_from_image(img_file)
    if not read_ok:
        raise ValueError('Unable to read image tags for file "%s"' % img_file)
    # now check the tags themselves:
    if not set(in_tags).issubset(set(read_tags)):
        msg = 'Image metadata tags read from file "%s"' % img_file
        msg += 'do not match the expected tags.\n'
        msg += '  Input tags:\n'
        for key, val in in_tags.items():
            msg += '     "%s" : "%s"\n' % (key, val)
        msg += '  Tags read from file:\n'
        for key, val in read_tags.items():
            msg += '     "%s" : "%s"\n' % (key, val)
        raise ValueError(msg)

def define_img_dict_in_tuple(in_tuple):
    '''
    A wrapper that defines an ImageDict from a dictionary of images and metadata.
    The input is a tuple so it can be parallelised.
    '''

    sub_dict = in_tuple[0]
    tag_order = in_tuple[1]
    skip_key_relist = in_tuple[2]
    selector_animated = in_tuple[3]
    animation_direction = in_tuple[4]

    img_dict = None
    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step,
    # which I might include below:
    for img_file, img_info in sub_dict.iteritems():
        tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tag_order)
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict,
                                     selector_animated=selector_animated,
                                     animation_direction=animation_direction)
        else:
            # the skip_key_relist option is useful to set to True for Large dictionaries.
            # It stops the key lists being regenerated each time something is appended.
            img_dict.append(imt.ImageDict(tmp_dict), skip_key_relist=skip_key_relist)

    return img_dict

def __main__():

    # parse the arguments, straight fail if there's a problem.
    parser = argparse.ArgumentParser(\
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                        description="Test routine for ImageMetaTag")
    parser.add_argument('--skip-plotting', '-s', action='store_true', dest='skip_plotting', \
                        help='Skip making plots, if test plot metadata is available', default=False)
    parser.add_argument('--no-big-dict', action='store_true', dest='no_biggus_dictus', \
                        help='Skip the big dictionary test.', default=False)
    args = parser.parse_args()

    n_random_data = 5
    random_data = make_random_data(n_random_data)

    webdir = get_webdir()
    os.chdir(webdir)
    # img_savedir is now relative to webdir:
    img_savedir = 'images'
    mkdir_p(img_savedir)
    # a database to store the image metadata, as we write them:
    imt_db = '%s/imt.db' % webdir

    compression_levels = [0, 1, 2, 3]
    trims = [True, False]
    borders = [5, 10, 100]

    borders_str = ['%s pixels' % border for border in borders]

    # colours to plot with, and the names we want in the metadata/webpage
    colours = [('r', 'Plotted in Red'),
               ('b', 'Plotted in Blue'),
               ('k', 'Plotted in Black'),
               ('g', 'Plotted in Green')]

    img_format = 'png'

    # this defines the order of the different tags in
    # the ImageDict, and so how they are displayed on the webpage:
    tagorder = ['number of rolls',
                'plot type',
                'plot color',
                'image trim',
                'border',
                'image compression']
    selector_animated = 4 # animate the image compression
    animation_direction = +1 # move forwards
    sort_methods = ['numeric', 'sort', 'sort', 'sort', borders_str, 'sort']
    plot_owner = 'Created by %s' % get_user_and_email()

    images_and_tags = {}

    metadata_pickle = '%s/meta.p' % img_savedir
    if not (args.skip_plotting and os.path.isfile(metadata_pickle) and os.path.isfile(imt_db)):
        if os.path.isfile(imt_db):
            print 'Deleting pre-exising image database "%s"' % imt_db
            os.remove(imt_db)
        # now plot the random data in some different ways, tagging the image as we go:
        for i_rand in range(n_random_data):
            for (plot_col, col_name) in colours:
                new_imgs_tags = plot_random_data(random_data, i_rand, plot_col,
                                                 col_name, trims, borders,
                                                 compression_levels, img_savedir,
                                                 img_format, plot_owner,
                                                 imt_db)
                # now stick the new img ingo into the main dict:
                for img_file, img_info in new_imgs_tags.iteritems():
                    images_and_tags[img_file] = img_info

        print_simple_timer(DATE_START, datetime.now(), 'plotting')
        with open(metadata_pickle, "wb") as open_pickle:
            pickle.dump(images_and_tags, open_pickle)

    else:
        # load the metadata from the pickle
        print 'loading metadata from %s' % metadata_pickle
        with open(metadata_pickle, "rb") as open_pickle:
            images_and_tags = pickle.load(open_pickle)

    img_dict = None

    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step as done below:
    for img_file, img_info in images_and_tags.iteritems():
        tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tagorder)
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict, selector_animated=selector_animated,
                                     animation_direction=animation_direction)
        else:
            img_dict.append(imt.ImageDict(tmp_dict))

    # this test the same thing, but created in parallel. This isn't needed for a small
    # set of plots like this example, but the code appears to scale well.
    # (within the Met Office, this code is used to produce internal web pages with 200,000+ images).

    # we are also going to construct it using data loaded in from the imt_db file, rather
    # than the list and metadata built up by the plotting. Read in by:
    #
    # this simply loads ALL of the image metadata:
    db_img_list, db_images_and_tags = imt.db.read_img_info_from_dbfile(imt_db)
    #
    # now verfiy the integrity of the database, relative to the plotting/pickling process:
    img_list = sorted(images_and_tags.keys())
    db_img_list.sort()
    if not img_list == db_img_list:
        raise ValueError('List of plots differ between database and plotting/pickle versions')
    if not images_and_tags == db_images_and_tags:
        raise ValueError('images_and_tags differ between database and plotting/pickle versions')
    #
    # For memory optimisation of large image databases, we want to make sure the dictionary
    # we get back is as small as possible in memory:
    #
    # these are the tags that we actually need to work with for the web page:
    required_tags = ['number of rolls', 'plot type', 'plot color',
                     'image trim', 'border', 'image compression']
    db_img_list, db_images_and_tags = imt.db.read_img_info_from_dbfile(imt_db,
                                                                       required_tags=required_tags)
    # and this will return a list of all of the unique metadata strings,
    # as there is a lot of duplication, and the returned db_images_and_tags will
    # reference the strings witin that list, rahter than contain the duplicated strings:
    tag_strings = []
    db_img_list, db_images_and_tags = imt.db.read_img_info_from_dbfile(imt_db,
                                                                       tag_strings=tag_strings)
    # and this both filters out un-needed tags and uses the tag_strings list as a reference
    tag_strings = []
    db_img_list, db_images_and_tags = imt.db.read_img_info_from_dbfile(imt_db,
                                                                       required_tags=required_tags,
                                                                       tag_strings=tag_strings)

    # now make the next page:
    n_proc = 4
    skip_key_relist = True
    extra_opts = (tagorder, skip_key_relist, selector_animated, animation_direction)
    subdict_gen = imt.dict_split(db_images_and_tags, n_split=n_proc, extra_opts=extra_opts)
    if n_proc == 1:
        # much easier to debug when not using the parallel calls:
        pool_out = []
        for in_tuple in subdict_gen:
            # now run the web_dir_process_images, and append the output to pool_out
            pool_out.append(define_img_dict_in_tuple(in_tuple))
    else:
        # now in parallel:
        proc_pool = Pool(n_proc)
        pool_out = proc_pool.map(define_img_dict_in_tuple, subdict_gen)
        proc_pool.close()
        proc_pool.join()



    # now stitch the parallel image dict back together:
    img_dict_para = pool_out[0]
    for i_dict in range(1, len(pool_out)):
        img_dict_para.append(pool_out[i_dict])

    if skip_key_relist:
        # if we skipped relisting the keys (as it's faster to do that)
        # then make sure we list them at the end:
        img_dict_para.list_keys_by_depth()


    # sort the keys:
    img_dict.sort_keys(sort_methods)
    img_dict_para.sort_keys(sort_methods)

    # now these should be the same, on a print:
    print img_dict
    print img_dict_para


    # now reorganise the img_dict to merge some of the images together (to display multiple images)
    #
    # This is best done after an ImageDict has been created that describes all of the images,
    # so we can use it to quickly group images togehter, rahter than having to search the
    # long list, or database, each time. This is much quicker.
    #
    # this defines the tag in the tagorder that we are grouping over.
    # It is a single integer, NOT a list as only a single tag is grouped in the code below.
    # In this case it is focusing on the plot color:
    multi_depth = 2
    # the key_filter can be used to filter out images to go on the web page, as well as report is
    # they are part of a special list for multiple images:
    # (a filter value of None means a filter is not applied, not that nothing passes the filter)
    key_filter = {'number of rolls': img_dict.keys[0][1:4], # subset these, as a test
                  'plot type': None,
                  'plot color': [img_dict.keys[multi_depth][0]] +
                                [('Primary colors', img_dict.keys[multi_depth][1:])] +
                                [('All colors', img_dict.keys[multi_depth])],
                  'image trim': None,
                  'border': None,
                  'image compression': None}
    # does the multi image require that ALL of the images is specifies are available,
    # in order to present anything?
    multi_req_all = True

    # now do the work to reorganise (with a time around it):
    date_start_reorg_multi = datetime.now()

    # This returns a copy of the previous image dict:
    img_dict_multi = img_dict.copy_except_dict_and_keys()
    img_dict_multi.dict = {}

    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step as done below:
    for img_file, img_info in images_and_tags.iteritems():
        # test the image to see if its needed, and if it's needed
        # for the complex/multiple image case:
        use_plain, use_multi, first_multi = imt.simple_dict_filter(img_info, key_filter)

        if use_plain:
            # just add the image, as is:
            tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tagorder)
            img_dict_multi.append(imt.ImageDict(tmp_dict))

        # now we are filterig one of the levels of the dict (multi_depth) by the multi_keys list:
        if use_multi and first_multi:
            for tuple_test in key_filter[tagorder[multi_depth]]:
                if isinstance(tuple_test, tuple):
                    # split the tuple test up into meaningful variable names:
                    group_name = tuple_test[0] # the name, as it will be in img_dict_multi
                    group_values = tuple_test[1] # the contents that will be grouped together

                    # now check that the image is the first element of this tuple_test:
                    if img_info[tagorder[multi_depth]] == group_values[0]:
                        # lookup to see if this combination has already been
                        # added to img_dict_multi. do this by creating a list of keys to
                        # lookup within the ImageDict:
                        img_dict_key_lookup = [img_info[x] for x in tagorder]
                        img_dict_key_lookup[multi_depth] = group_name

                        if len(img_dict_multi.dict) == 0:
                            already_in_img_dict_multi = False
                        else:
                            if img_dict_multi.return_from_list(img_dict_key_lookup) is None:
                                already_in_img_dict_multi = False
                            else:
                                already_in_img_dict_multi = True

                        if already_in_img_dict_multi:
                            print 'multi image already added!'
                            print img_dict_key_lookup
                            #msg = 'Adding a multi-image that has already been added.'
                            #msg += ' Checks on first_image_multi should prevent that.'
                            #raise ValueError(msg)
                        else:
                            # this group hasn't already been added to the img_dict_multi:

                            if group_name in img_dict.keys[multi_depth]:
                                # the group_name shouldn't be the same as a key that identifies a
                                # single image. That will cause problems, and will change what is
                                # presented depening on the order that the img_file, img_info comes
                                # up in images_and_tags.iteritems()
                                msg = 'A multi image group has the same key name as a single image'
                                raise ValueError(msg)
                            all_img_relpaths = []

                            for this_value in group_values:
                                # now use the img_dict_key_lookup again,
                                # only this time looking for this_value
                                img_dict_key_lookup[multi_depth] = this_value
                                # and look in the main img_dict as that already has all the images,
                                # sorted and easily accessible:
                                all_img_relpaths.append(img_dict.return_from_list(img_dict_key_lookup))
                                #
                                # If more complicated processing is required, substitutions or
                                # fudging values, then this could be done here.


                            if multi_req_all and any([x is None for x in all_img_relpaths]):
                                # we need all images in this list, and one fails, so just pass:
                                pass
                            else:
                                # now create a multi element dict, pretending to be an
                                # image with the same properties:
                                tmp_img_info = {}
                                for tag_name in tagorder:
                                    tmp_img_info[tag_name] = img_info[tag_name]
                                # with the exception of the one at multi_depth, which is the group_name:
                                tmp_img_info[tagorder[multi_depth]] = group_name

                                tmp_dict = imt.dict_heirachy_from_list(tmp_img_info,
                                                                       all_img_relpaths,
                                                                       tagorder)
                                img_dict_multi.append(imt.ImageDict(tmp_dict))

                else:
                    # this test is a standard one, not a tuple defining a multi image, so just pass:
                    pass

    # sort img_dict_multi - the sorter will need to include new info though
    sort_multi = copy.deepcopy(sort_methods)
    # now get the sort order from the key_filter:
    sort_multi[multi_depth] = [x[0] if isinstance(x, tuple) else x for x in key_filter[tagorder[multi_depth]]]
    # and sort
    img_dict_multi.sort_keys(sort_multi)

    # end timer:
    print_simple_timer(date_start_reorg_multi, datetime.now(), 'reorg_multi')


    # now do this again, this time using the database as the
    # source of informaiton, rather than a pre-created ImageDict.
    # This is to test the speed of different approaches, and test the functionality.
    del img_dict_multi
    date_start_reorg_multi2 = datetime.now()

    # This returns a copy of the previous image dict:
    img_dict_multi = img_dict.copy_except_dict_and_keys()
    img_dict_multi.dict = {}

    # becasue we are going to do a lot of searches,
    # we need to read the imt_db into memory for fast access:
    print 'reading database file: %s' % imt_db
    dbcn, dbcr = imt.db.read_db_file_to_mem(imt_db)
    print 'db file read'

    # now assemble the ImageDict:
    # This is the simple way, but it is possible to parallelise this step as done below:
    for img_file, img_info in images_and_tags.iteritems():
        # test the image to see if its needed, and if it's
        # needed for the complex/multiple image case:
        use_plain, use_multi, first_multi = imt.simple_dict_filter(img_info, key_filter)

        if use_plain:
            # just add the image, as is:
            tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tagorder)
            img_dict_multi.append(imt.ImageDict(tmp_dict))

        # now we are filterig one of the levels of the dict (multi_depth) by the multi_keys list:
        if use_multi and first_multi:
            for tuple_test in key_filter[tagorder[multi_depth]]:
                if isinstance(tuple_test, tuple):
                    # split the tuple test up into meaningful variable names:
                    group_name = tuple_test[0] # the name, for img_dict_multi
                    group_values = tuple_test[1] # the contents that will be grouped

                    # now check that the image is the first element of this tuple_test:
                    if img_info[tagorder[multi_depth]] == group_values[0]:
                        # first of all, lookup to see if this combination has already been
                        # added to img_dict_multi. do this by creating a list of keys to
                        # lookup within the ImageDict:
                        img_dict_key_lookup = [img_info[x] for x in tagorder]
                        img_dict_key_lookup[multi_depth] = group_name

                        if len(img_dict_multi.dict) == 0:
                            already_in_img_dict_multi = False
                        else:
                            if img_dict_multi.return_from_list(img_dict_key_lookup) is None:
                                already_in_img_dict_multi = False
                            else:
                                already_in_img_dict_multi = True

                        if already_in_img_dict_multi:
                            msg = 'Adding a multi-image that has already been added.'
                            msg = ' Checks on first_image_multishould prevent that.'
                            raise ValueError(msg)
                        else:
                            # this group hasn't already been added to the img_dict_multi:

                            if group_name in img_dict.keys[multi_depth]:
                                # the group_name shouldn't be the same as a key that identifies
                                # a single image. That will cause problems, and will change what
                                # is presented depening on the order that the img_file, img_info
                                # comes up in images_and_tags.iteritems()
                                msg = 'A multi image group has the same key name as a single image'
                                raise ValueError(msg)
                            all_img_relpaths = []

                            for this_value in group_values:

                                # now produce a set of tags to search teh databse for:
                                select_tags = {}
                                for i_tag, tag_name in enumerate(tagorder):
                                    if i_tag == multi_depth:
                                        select_tags[tag_name] = this_value
                                    else:
                                        select_tags[tag_name] = img_info[tag_name]
                                # and look in the main img_dict as that already
                                # has all the images, sorted and easily accessible:
                                sel_file_list, _ = imt.db.select_dbcr_by_tags(dbcr, select_tags)
                                if len(sel_file_list) == 1:
                                    all_img_relpaths.append(sel_file_list[0])
                                else:
                                    all_img_relpaths.append(None)

                            if multi_req_all and any([x is None for x in all_img_relpaths]):
                                # we need all images in this list, and one fails, so just pass:
                                pass
                            else:
                                # now create a multi element dict, pretending
                                # to be an image with the same properties:
                                tmp_img_info = {}
                                for tag_name in tagorder:
                                    tmp_img_info[tag_name] = img_info[tag_name]
                                # with the exception of the one at multi_depth, which is the group_name:
                                tmp_img_info[tagorder[multi_depth]] = group_name

                                tmp_dict = imt.dict_heirachy_from_list(tmp_img_info,
                                                                       all_img_relpaths, tagorder)
                                img_dict_multi.append(imt.ImageDict(tmp_dict))

                else:
                    # this test is a standard one, not a tuple defining a multi image, so just pass:
                    pass

    # clost the db copy now we're done
    dbcn.close()

    # sort img_dict_multi - the sorter will need to include new info though
    sort_multi = copy.deepcopy(sort_methods)
    # now get the sort order from the key_filter:
    sort_multi[multi_depth] = [x[0] if isinstance(x, tuple) else x for x in key_filter[tagorder[multi_depth]]]
    # and sort
    img_dict_multi.sort_keys(sort_multi)

    # end timer:
    print_simple_timer(date_start_reorg_multi2, datetime.now(), 'reorg_multi from database')

    # now create a web page for each of them:
    out_page = '%s/page.html' % webdir
    out_page_para = '%s/page_para.html' % webdir
    out_page_multi = '%s/page_multi.html' % webdir

    shutil.copy(LOGO_FILE, '%s/logo.png' % webdir)

    webpage_preamble = '''
<div id='logo' style='float:left;'>
  <img src=logo.png></td>
</div>
<div id='preamble'>
    <p>&nbsp;</p>
    <h1>This is a test page for the ImageMetaTag module.</h1>
</div>
'''

    # add a post-amble, including some server side
    #includes for last-modified, and a disk usage string.
    webpage_postamble = r'''
<div id='postamble'>
  This page was last modified
  <!--#config timefmt="%H:%M, %d %B %Y" -->
  <!--#echo var="LAST_MODIFIED"--><br>
'''
    webpage_postamble += plot_owner
    webpage_postamble += '\n</div>'

    # for the test page, we want to start the page on an image that isn't the first one:
    for i_key in range(len(img_dict.keys)):
        if i_key == 0:
            # start at random:
            initial_selectors = [random.choice(img_dict.keys[i_key])]
        else:
            # select a new selector, at random, from those
            # which are consistent with the current tree:
            next_sel = random.choice(img_dict.return_from_list(initial_selectors).keys())
            initial_selectors.append(next_sel)

    # now write out the webpages:
    imt.webpage.write_full_page(img_dict, out_page,
                                'Test ImageDict webpage',
                                preamble=webpage_preamble, postamble=webpage_postamble,
                                initial_selectors=initial_selectors,
                                verbose=True, internal=False, only_show_rel_url=True)
    imt.webpage.write_full_page(img_dict, out_page_para,
                                'Test ImageDict webpage (Parallel version)',
                                preamble=webpage_preamble, postamble=webpage_postamble,
                                verbose=True, internal=False, only_show_rel_url=False)
    imt.webpage.write_full_page(img_dict_multi, out_page_multi,
                                'Test ImageDict webpage (mutli image version)',
                                preamble=webpage_preamble, postamble=webpage_postamble,
                                verbose=True, internal=False, url_type='str')

    # now, finally, produce a large ImageDict:
    if not args.no_biggus_dictus:
        print 'Producing a very large ImageDict, as a scalability and speed test'
        # Make a large input dictionary, not actual images though.
        # That would take up a lot of disk space!
        # We don't need to be big or clever for this, it's a test, so simple and readable is fine.
        # factorial(9) is ~300K 'images', which is comparable in scale to the forecast monitoring
        # plots this code runs in the Met Office.

        # store this in a database:
        bigdb = '%s/big.db' % webdir
        first_img = True
        date_start_bigdb = datetime.now()
        biggus_dictus = {}
        i_count = 0
        n_to_do = np.math.factorial(9)
        n_to_do_flt = float(np.math.factorial(9))
        dt_prev = datetime.now()
        for i_1 in xrange(1):
            for i_2 in xrange(2):
                for i_3 in xrange(3):
                    for i_4 in xrange(4):
                        for i_5 in xrange(5):
                            for i_6 in xrange(6):
                                for i_7 in xrange(7):
                                    for i_8 in xrange(8):
                                        for i_9 in xrange(9):
                                            # we don't want to actually make an image!
                                            img_name = '%s/%s/%s/%s/%s/%s_%s_%s_%s_no_image.png ' \
                                                    % (i_1, i_2, i_3, i_4, i_5, i_6, i_7, i_8, i_9)
                                            img_info = {'l1': 'Lev 1: %s' % i_1,
                                                        'l2': 'Lev 2: %s' % i_2,
                                                        'l3': 'Lev 3: %s' % i_3,
                                                        'l4': 'Lev 4: %s' % i_4,
                                                        'l5': 'Lev 5: %s' % i_5,
                                                        'l6': 'Lev 6: %s' % i_6,
                                                        'l7': 'Lev 7: %s' % i_7,
                                                        'l8': 'Lev 8: %s' % i_8,
                                                        'l9': 'Lev 9: %s' % i_9}
                                            biggus_dictus[img_name] = img_info
                                            if first_img:
                                                bigdb_cn, bigdb_cr = imt.db.open_or_create_db_file(bigdb, img_info, restart_db=True)
                                                first_img = False
                                            imt.db.write_img_to_open_db(bigdb_cr, img_name, img_info)
                                            i_count += 1
                                            if i_count % 1000 == 0:
                                                dt_now = datetime.now()
                                                print '%s out of %s (%s%%) %s' % (i_count, n_to_do, 100 * i_count / n_to_do_flt,
                                                                                  dt_now - dt_prev)
                                                dt_prev = dt_now
        bigdb_cn.commit()
        bigdb_cn.close()
        print_simple_timer(date_start_bigdb, datetime.now(),
                           'Producing large dictionary and database')

        # TODO: run through the big dict, and delete 1 in 10 images from the database
        # a) all as one list
        # b) all as one list, but commit after each
        # c) one at a time, committing and closing
        #
        # expect c to be much slower, but how different is b), also how much better
        # is b than a at having a database lock/unlock...

        tagorder = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8', 'l9']
        print '  input dictionary complete, with %s elements' % len(biggus_dictus)

        db_img_list, db_images_and_tags = imt.db.read_img_info_from_dbfile(bigdb)
        # verfiy the integrity of the database, relative to the plotting/pickling process:
        img_list = sorted(biggus_dictus.keys())
        db_img_list.sort()
        if not img_list == db_img_list:
            msg = 'List of plots differ between memory and database versions of big dict'
            raise ValueError(msg)
        if not biggus_dictus == db_images_and_tags:
            msg = 'images_and_tags differ between memory and database versions of big dict'
            raise ValueError(msg)

        # now process that big dict in parallel:
        date_start_big = datetime.now()
        n_proc = 8
        # for large dictionaries, we really do want this skip_key_relist set to True,
        # as it saves a lot of time:
        skip_key_relist = True
        subdict_gen = imt.dict_split(biggus_dictus, n_split=n_proc,
                                     extra_opts=(tagorder, skip_key_relist, None, None))
        if n_proc == 1:
            # much easier to debug when not using the parallel calls:
            pool_out = []
            for in_tuple in subdict_gen:
                # now run the web_dir_process_images, and append the output to pool_out
                pool_out.append(define_img_dict_in_tuple(in_tuple))
        else:
            # now in parallel:
            proc_pool = Pool(n_proc)
            pool_out = proc_pool.map(define_img_dict_in_tuple, subdict_gen)
            proc_pool.close()
            proc_pool.join()
        # now stitch the parallel image dict back together:
        biggus_dictus_imigus = pool_out[0]
        for i_dict in range(1, len(pool_out)):
            biggus_dictus_imigus.append(pool_out[i_dict])

        # because we have appended to the dict without regenerating the lists, so do that now:
        biggus_dictus_imigus.list_keys_by_depth()
        print_simple_timer(date_start_big, datetime.now(), 'Large parallel dict processing')
        # and now make we big dict webpage (and time it too)
        date_start_web = datetime.now()
        out_page_big = '%s/biggus_pageus.html' % webdir
        imt.webpage.write_full_page(biggus_dictus_imigus, out_page_big,
                                    'Test ImageDict webpage', verbose=True, internal=False)
        print_simple_timer(date_start_web, datetime.now(), 'Large parallel dict webpage')


if __name__ == '__main__':
    __main__()
