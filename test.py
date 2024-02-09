'''
Produces a set of test plots using matplotlib, with just random data.

Each plot is tagged with appropriate metadata, and an ImageDict produced
which describes them and creates a web page.

.. moduleauthor:: Melissa Brooks https://github.com/melissaebrooks

(C) Crown copyright Met Office. All rights reserved.
Released under BSD 3-Clause License. See LICENSE for more details.
'''

# standard python modules:
import os
import shutil
import sys
import errno
import argparse
import copy
import random
import platform
import math
import pdb
from multiprocessing import Pool
from datetime import datetime

# common python modules:
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# for timings:
DATE_START = datetime.now()
# ensure batch plotting works:
matplotlib.use('Agg')

# python2/3 specific modules:
PY3 = sys.version_info[0] == 3
if PY3:
    import pickle
else:
    import cPickle as pickle

# import ImageMetaTag, the module this routine is testing, so that the
# test is using the version of ImageMetaTag associated with the test script:
# (this would normally be added already, by installation, but for testing, we
#  need to be testing the version we are making changes too!)
TEST_PATH = os.sep.join(os.path.abspath(sys.argv[0]).split(os.sep)[0:-1])
sys.path.insert(0, TEST_PATH)

# and the location of the dir for test rousoruces (stock problem images etc.)
TEST_RESOURCES = os.path.join(TEST_PATH, 'test_resources')

# Now, import ImageMetaTag to do things:
import ImageMetaTag as imt


LOGO_FILE = os.path.join(TEST_PATH, 'logo.png')
LOGO_SIZE = 60
LOGO_PADDING = 5

# set the detailed format to print to stdout:
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
# and a more friendly format for the output webpages:
DATE_FORMAT_WWW = "%Y-%m-%d"

# before we do anything, report where ImageMetaTag is from:
print('ImageMetaTag from "{}"'.format(imt.__path__[0]))


def get_webdir(minimal=False):
    '''
    Works out the location to use as webdir in this test run. This is done in
    a function only because it can be imported into simplest_img_dict.py to
    keep it consistent. In a real application you can just specify a location
    on your file system that is web-accessible.
    '''
    home = os.getenv('HOME')
    webdir = None

    if minimal:
        imt_subdir = os.path.join('ImageMetaTagTest', 'minimal')
    else:
        imt_subdir = 'ImageMetaTagTest'

    dirs_to_check = ['%s/public_html' % home, '%s/Public' % home]
    for check_dir in dirs_to_check:
        if os.path.isdir(check_dir):
            webdir = os.path.join(check_dir, imt_subdir)
            break
    if not webdir:
        msg = 'Cannot find appropriate web dir from: {}'
        raise ValueError(msg.format(dirs_to_check))

    # make it if it doesn't exist:
    if not os.path.isdir(webdir):
        mkdir_p(webdir)

    return webdir


def define_imt_db(wipe=False, minimal=False):
    'Defines the main database file to use to the image metadate:'
    imt_db = '{}/imt.db'.format(get_webdir(minimal=minimal))
    if wipe and os.path.isfile(imt_db):
        os.remove(imt_db)

    return imt_db


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


def make_random_data(n_random_data, seed=3):
    '''
    generates some data sets of random data, simulating rolling 2 D6 a number
    of times. In order to produce predictable random data for testing, the
    random seed needs to be initialised.
    By default the seed is 3:
         "Then, shalt thou count to three. No more. No less."
    '''
    random_data = []
    # simulate rolling 2 6 sided dice:
    np.random.seed(seed)
    for i_rand in range(n_random_data):
        # make some actual random data:
        if i_rand < 6:
            n_rolls = 6 ** (i_rand + 1)
        else:
            n_rolls = 6 ** (6) + 2 ** (i_rand + 1)
        random_data.append(np.random.randint(1, 6, n_rolls) +
                           np.random.randint(1, 6, n_rolls))
    return random_data


def plot_random_data(random_data, i_rand, plot_col, col_name, trims, borders,
                     compression_levels, dpis, img_savedir, img_format, plot_owner,
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
        plt.title(('Sum of two random integers between 1 and 6, with '
                   'an extremely long title.\n'))
    else:
        plt.title('Sum of two random integers between 1 and 6\n')

    # make the subdirectories:
    mkdir_p('{}/rolls'.format(img_savedir))
    mkdir_p('{}/dists'.format(img_savedir))

    data_source = 'Some random data'

    img_count = 0

    # save the figure, using different image-meta-tag options
    # and tag the images.
    for trim in trims:
        if trim:
            these_borders = borders
        else:
            these_borders = [0]
        for border in these_borders:
            for compression in compression_levels:
                for dpi in dpis:
                    outfile = '%s/rolls/imt_%s_%s_compression_%s' \
                            % (img_savedir, n_rolls, plot_col, compression)
                    outfile = 'imt_{}_{}_comp{}_{}dpi'.format(n_rolls,
                                                               plot_col,
                                                               compression,
                                                               dpi)
                    outfile = os.path.join(img_savedir, 'rolls', outfile)
                    if trim:
                        outfile += '_trim_b%s' % border
                        trim_str = 'Image trimmed'
                    else:
                        trim_str = 'Image untrimmed'
                    outfile += '.{}'.format(img_format)
                    # image tags for the web page:
                    img_tags = {'number of rolls': '{} simulated rolls'.format(n_rolls),
                                'plot type': 'Line plots',
                                'image compression': 'Compression option {}'.format(compression),
                                'image trim': trim_str,
                                'border': '{} pixels'.format(border),
                                'plot color': col_name,
                                'expected dpi': '{} dpi'.format(dpi)}

                    # and other, more general tags showing the sort of
                    # thing that might be useful:
                    img_tags['data source'] = data_source
                    img_tags['plot owner'] = plot_owner
                    img_tags['plot created by'] = this_routine
                    img_tags['ImageMetaTag version'] = imt.__version__
                    if img_count > 1 and img_count < 10:
                        # only add this one after the database exists,
                        # to test expandning the database:
                        img_tags['SQL-char-name:in_tag'] = 'testing SQL chars'
                    # now save the file with imt.savefig
                    # (deleting any pre-existing file first):
                    if os.path.isfile(outfile):
                        os.remove(outfile)
                    imt.savefig(outfile, do_trim=trim, trim_border=border,
                                do_thumb=True, img_converter=compression,
                                img_tags=img_tags, keep_open=True,
                                verbose=imt_verbose,
                                db_file=imt_db, db_timeout=db_timeout,
                                db_add_strict=False,
                                dpi=dpi,
                                logo_file=LOGO_FILE, logo_width=LOGO_SIZE,
                                logo_padding=LOGO_PADDING, logo_pos=0)
                    # now store those tags
                    images_and_tags[outfile] = img_tags
                    # and check they are the same as those that come from reading
                    # the image metatadata from disk:
                    check_img_tags(outfile, img_tags)
                    img_count += 1

    plt.close()
    outfile = '%s/dist_%s_%s.%s' % (img_savedir, n_rolls, plot_col, img_format)
    if PY3:
        _count, _bins, _ignored = plt.hist(random_data[i_rand],
                                           [x + 0.5 for x in range(13)],
                                           color=plot_col, density=True)
    else:
        _count, _bins, _ignored = plt.hist(random_data[i_rand],
                                           [x + 0.5 for x in range(13)],
                                           color=plot_col, normed=True)

    plt.xlim([1, 13])
    plt.title('Distribution of %s random integers between 1 and 6\n' % n_rolls)

    for trim in trims:
        if trim:
            these_borders = borders
        else:
            these_borders = [0]
        for border in these_borders:
            for compression in compression_levels:
                for dpi in dpis:
                    outfile = 'imt_{}_{}_comp{}_{}dpi'.format(n_rolls,
                                                               plot_col,
                                                               compression,
                                                               dpi)
                    outfile = os.path.join(img_savedir, 'dists', outfile)
                    if trim:
                        outfile += '_trim_b%s' % border
                        trim_str = 'Image trimmed'
                    else:
                        trim_str = 'Image untrimmed'
                    outfile += '.{}'.format(img_format)
                    # tags to drive web page:
                    img_tags = {'number of rolls': '{} simulated rolls'.format(n_rolls),
                                'plot type': 'Histogram',
                                'image compression': 'Compression option {}'.format(compression),
                                'image trim': trim_str,
                                'border': '{} pixels'.format(border),
                                'plot color': col_name,
                                'expected dpi': '{} dpi'.format(dpi)}
                    # again, more general tags:
                    img_tags['data source'] = data_source
                    img_tags['plot owner'] = plot_owner
                    img_tags['plot created by'] = this_routine
                    img_tags['ImageMetaTag version'] = imt.__version__
                    img_tags['SQL-char-name:in_tag'] = 'testing SQL chars'
                    # now save the file with imt.savefig
                    # (deleting any pre-existing file first):
                    if os.path.isfile(outfile):
                        os.remove(outfile)
                    imt.savefig(outfile, do_trim=trim, trim_border=border,
                                do_thumb=True, img_converter=compression,
                                img_tags=img_tags, keep_open=True,
                                verbose=imt_verbose,
                                db_file=imt_db, db_timeout=db_timeout,
                                db_add_strict=False,
                                dpi=dpi,
                                logo_file=[LOGO_FILE, LOGO_FILE],
                                logo_height=LOGO_SIZE//2,
                                logo_padding=LOGO_PADDING, logo_pos=[1, 1])
                    # log tags:
                    images_and_tags[outfile] = img_tags
                    # and check:
                    check_img_tags(outfile, img_tags)
                    img_count += 1
    plt.close()

    # NOTE: in actual usage, it's easier to refer to the database when you
    # need to get image metadata. In this test script we need to test the
    # integrity of the database, so we need to pass back the images
    # and tags we expect:
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
        else:
            raise


def print_simple_timer(dt_start, dt_end, label):
    'prints out a simple timer message'
    msg = '{}: started at {}, completed at {}, taking {}'
    print(msg.format(label,
                     dt_start.strftime(DATE_FORMAT),
                     dt_end.strftime(DATE_FORMAT),
                     (dt_end - dt_start)))


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
        for key, val in list(in_tags.items()):
            msg += '     "%s" : "%s"\n' % (key, val)
        msg += '  Tags read from file:\n'
        for key, val in list(read_tags.items()):
            msg += '     "%s" : "%s"\n' % (key, val)
        raise ValueError(msg)


def define_img_dict_in_tuple(in_tuple):
    '''
    Defines a simple ImageDict from a dictionary of images and metadata.
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
    for img_file, img_info in sub_dict.items():
        tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tag_order)
        if not tmp_dict:
            raise ValueError('Input dict does not contain the required keys')
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict,
                                     selector_animated=selector_animated,
                                     animation_direction=animation_direction)
        else:
            # the skip_key_relist option is useful to set to True for Large
            # dictionaries. It stops the key lists being regenerated each time
            # something is appended.
            img_dict.append(imt.ImageDict(tmp_dict),
                            skip_key_relist=skip_key_relist)
    return img_dict


def make_test_css(webdir):
    'writes out a test.css file in a specified directory'

    css_file = os.path.join(webdir, 'test.css')

    css_content = '''body {
  background-color: #d3eeed;
  color: black;
}
body, div, dl, dt, dd, li, h1, h2 {
  margin: 0;
  padding: 0;
}
h3, h4, h5, h6, pre, form, fieldset, input {
  margin: 0;
  padding: 0;
}
textarea, p, blockquote, th, td {
  margin: 0;
  padding: 0;
}
fieldset, img {
  border: 0 none;
}
body {
  font: 12px Myriad,Helvetica,Tahoma,Arial,clean,sans-serif;
  *font-size: 75%;
}
h1 {
  font-size: 1.5em;
  font-weight: normal;
  line-height: 1em;
  margin-top: 1em;
  margin-bottom:0;
}
h2 {
  font-size: 1.1667em;
  font-weight: bold;
  line-height: 1.286em;
  margin-top: 1.929em;
  margin-bottom:0.643em;
}
h3, h4, h5, h6 {
  font-size: 1em;
  font-weight: bold;
  line-height: 1.5em;
  margin-top: 1.5em;
  margin-bottom: 0;
}
p {
  font-size: 1em;
  margin-top: 1.5em;
  margin-bottom: 1.5em;
  line-height: 1.5em;
}
pre, code {
  font-size:115%;
  *font-size:100%;
  font-family: Courier, "Courier New";
  background-color: #efefef;
  border: 1px solid #ccc;
}
pre {
  border-width: 1px 0;
  padding: 1.5em;
}
table {
  font-size:100%;
}
'''
    with open(css_file, 'w') as file_obj:
        file_obj.write(css_content)
    return css_file


def test_key_sorting():
    '''
    Tests that the different variants of sorting in an ImageDict work
    are working correctly. These are not all used in the type of web pages
    used in the main tests so they are tested directly.
    '''

    # for each type of test, define the input keys and how they should be when
    # they are sorted:
    sort_tests = {}

    # a straight alphabetical sort - the tuple here gives the
    # (input, expected output) for the type of sort:
    sort_tests['sort'] = (['aaa', 'zaa', 'aba', '257', 'bob'],
                          ['257', 'aaa', 'aba', 'bob', 'zaa'])
    # a reversed alphabetical sort:
    sort_tests['reverse sort'] = (['aaa', 'zaa', 'aba', '257', 'bob'],
                                  ['zaa', 'bob', 'aba', 'aaa', '257'])
    # T+ - used for forecast lead times, so sort by the value after the T+
    # and anything with None gets alphabetically sorted at the end
    sort_tests['T+'] = (['T+0', 'T+1', 't+10', 'T+2', 't-3',
                         'T+None', 't-None', 'None'],
                        ['t-3', 'T+0', 'T+1', 'T+2', 't+10',
                         'None', 'T+None', 't-None'])
    # here, we will use a list to sort by, and anything not in the list
    # gets a simple sort:
    sort_by_list = ['aaa', 'zaa']
    sort_tests['sort_by_list'] = (['aaa', 'zaa', 'aba', '257', 'bob'],
                                  ['aaa', 'zaa', '257', 'aba', 'bob'])
    # a set of numeric values common in meteorology:
    sort_tests['numeric'] = (['10m', '50m', '4mm', '62 hPa', '2m', '16 km',
                              'Model level 7', 'Surface', '12mb', '341.434646',
                              'Eastern England',
                              '3.344E, 16.7N', '2.344E, 18.7N', '16.0 nm'],
                             ['Surface', '16.0 nm', '4mm', '2m', '10m', '50m',
                              '16 km', '62 hPa', '12mb', 'Model level 7',
                              '2.344E, 18.7N', '3.344E, 16.7N', '341.434646',
                              'Eastern England',])
    # these get used/modified while prepping the sort:
    sort_tests_copy = copy.deepcopy(sort_tests)

    test_order = sorted(sort_tests.keys())
    n_sorts_to_test = len(test_order)
    # make a dummy ImageDict
    dummy_tag_order = []
    dummy_tag_info = {}
    for level in range(n_sorts_to_test):
        lname = 'l{}'.format(level)
        dummy_tag_order.append(lname)
        dummy_tag_info[lname] = str(level)
    tmp_dict = imt.dict_heirachy_from_list(dummy_tag_info,
                                           'None', dummy_tag_order)
    img_dict = imt.ImageDict(tmp_dict)

    # now overide the keys of imd_dict with the keys we want to test,
    # and make the list of how each level is to be sorted:
    sort_methods = []
    for level, test_name in enumerate(test_order):
        img_dict.keys[level] = sort_tests[test_name][0]
        if test_name == 'sort_by_list':
            sort_methods.append(sort_by_list)
        else:
            sort_methods.append(test_name)
    # now do the sort:
    img_dict.sort_keys(sort_methods)

    # now go through the sort methods and check the output is as expected:
    failed = False
    for level, test_name in enumerate(test_order):
        if img_dict.keys[level] == sort_tests[test_name][1]:
            pass
        else:
            msg = ('Sort method test "{}" has failed to correctly'
                   'sort its ImageDict keys:\n'
                   '  Input list: {}\n'
                   '  Sorted list: {}\n'
                   '  Expected list: {}\n')
            print(msg.format(test_name,
                             sort_tests_copy[test_name][0],
                             img_dict.keys[level],
                             sort_tests[test_name][1]))
            failed = True

    return not failed


def test_compare_img_tags(img_tags1, name1, img_tags2, name2):
    '''
    Tests a set of images and metadata tags.
     * img_tags1 - dict of images, and their metadata tags
     * name1 - name of img_tags1 for error reporting only
     * img_tags2 - second dict of images, and their metadata tags
     * name2 - name of img_tags2 for error reporting only

    This is not a simple '==' test, as the database will have None when the
    item is missing for fields that are defined for some images, but not
    all, images.
    '''

    # firstly check the keys:
    imgs1 = sorted(img_tags1.keys())
    imgs2 = sorted(img_tags2.keys())
    if imgs1 != imgs2:
        in1_not2 = set(imgs1).difference(set(imgs2))
        in2_not1 = set(imgs2).difference(set(imgs1))

        msg = ('image names in img_tags1 differ to image names in img_tags2.\n'
               '  images in {0}(1), but not {1}(2): {2}\n'
               '  images in {1}(2), but not {0}(1): {3}')
        raise ValueError(msg.format(name1, name2, in1_not2, in2_not1))

    for img in imgs1:
        if img_tags1[img] != img_tags2[img]:
            # test that all of the keys for this img that are shared,
            # are equal:
            i_t_keys = set(img_tags1[img].keys())
            d_t_keys = set(img_tags2[img].keys())
            common_keys = i_t_keys.intersection(d_t_keys)
            for key in common_keys:
                if img_tags1[img][key] != img_tags2[img][key]:
                    msg = ('tags in "{}" for file "{}", tag "{}" ("{}") '
                           'different to that in "{}" ("{}")')
                    raise ValueError(msg.format(name1, img, key,
                                                img_tags1[img][key],
                                                name2, img_tags2[img][key]))

            # in the current tests, the only difference should be that
            # sometimes the 'SQL-char-name:in_tag' tag isn't present:
            keys_diff = i_t_keys.symmetric_difference(d_t_keys)
            if keys_diff != set(['SQL-char-name:in_tag']):
                msg = 'Unexpected difference in keys in databases: {}'
                raise ValueError(msg.format(keys_diff))


def __main__():

    # parse the arguments, straight fail if there's a problem.
    parser = argparse.ArgumentParser(
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                    description="Test routine for ImageMetaTag")
    parser.add_argument('--skip-plotting', '-s', action='store_true',
                        dest='skip_plotting', default=False,
                        help='Skip making plots, if metadata is available')
    parser.add_argument('--no-big-dict', action='store_true',
                        dest='no_biggus_dictus', default=False,
                        help='Skip the big dictionary test.')
    parser.add_argument('--no-db-rebuild', action='store_true',
                        dest='no_db_rebuild', default=False,
                        help='Skip rebuilding an image database from disk')
    parser.add_argument('--minimal', '-m', '-q', action='store_true',
                        dest='minimal', default=False,
                        help='Run only a minimal amount of testing')
    args = parser.parse_args()

    if args.minimal:
        n_random_data = 1
        compress_levels = [3]
        trims = [True]
        borders = [10]
        dpis = [None, 72, 300]
        # colours to plot with, and the names we want in the metadata/webpage
        colours = [('g', 'Plotted in Green')]
    else:
        n_random_data = 3
        compress_levels = [0, 1, 2, 3]
        trims = [True, False]
        borders = [5, 10, 100]
        dpis = [72, 150]
        # colours to plot with, and the names we want in the metadata/webpage
        colours = [('r', 'Plotted in Red'),
                   ('b', 'Plotted in Blue'),
                   ('k', 'Plotted in Black'),
                   ('g', 'Plotted in Green')]
    random_data = make_random_data(n_random_data)
    borders_str = ['{} pixels'.format(border) for border in borders]

    # working directory to create images and webpage etc.
    webdir = get_webdir(minimal=args.minimal)
    # The img_savedir is relative to webdir:
    img_savedir = os.path.join(webdir, 'images')
    mkdir_p(img_savedir)

    test_zlib_compression = True

    # a database to store the image metadata, as we write them:
    imt_db = define_imt_db(wipe=not args.skip_plotting, minimal=args.minimal)

    if not os.path.isfile(LOGO_FILE):
        raise ValueError('No logo file found at: %s' % LOGO_FILE)

    # set up the images we want to create in the test, and the webpages:
    img_format = 'png'
    # this defines the order of the different tags in
    # the ImageDict, and so how they are displayed on the webpage:
    tagorder = ['data source',
                'number of rolls',
                'plot type',
                'plot color',
                'image trim',
                'border',
                'expected dpi',
                'image compression']
    selector_animated = 5  # animate the image compression
    animation_direction = +1  # move forwards
    sort_methods = ['sort', 'numeric', 'sort', 'sort', 'sort',
                    borders_str, 'numeric', 'sort']
    plot_owner = 'Created by %s' % get_user_and_email()

    # what are the full names of those tags:
    tag_full_names = {'data source': 'Data Source',
                      'number of rolls': 'Number of rolls',
                      'plot type': 'Plot type',
                      'plot color': 'Plot color',
                      'image trim': 'Image trimmed?',
                      'border': 'Image border',
                      'image compression': 'Image compression',
                      'expected dpi': 'Expected DPI',
                      }
    sel_widths = {'data source': '120px',
                  'number of rolls': '180px',
                  'plot type': '120px',
                  'plot color': '200px',
                  'image trim': '150px',
                  'border': '140px',
                  'expected dpi': '90px',
                  'image compression': '200px',
                  }
    # if we want to present these, have them as an ordered list, by tagorder:
    sel_names_list = [tag_full_names[x] for x in tagorder]
    sel_widths_list = [sel_widths[x] for x in tagorder]

    # this will become a large dict of images and their metadata:
    images_and_tags = {}

    if PY3:
        metadata_pickle = '%s/meta.py3.p' % img_savedir
    else:
        metadata_pickle = '%s/meta.py2.p' % img_savedir
    # do we want to, and can we actually, skip ploting:
    skip_plot = (args.skip_plotting and
                 os.path.isfile(metadata_pickle) and
                 os.path.isfile(imt_db))
    if skip_plot:
        # load the metadata from the pickle
        print('loading metadata from %s' % metadata_pickle)
        with open(metadata_pickle, "rb") as open_pickle:
            images_and_tags = pickle.load(open_pickle)
    else:
        # do the work of making all the plots:
        if os.path.isfile(imt_db):
            print('Deleting pre-exising image database "%s"' % imt_db)
            os.remove(imt_db)
        # now plot the random data in some different ways,
        # tagging the image as we go:
        for i_rnd in range(n_random_data):
            for (plot_col, col_name) in colours:
                new_imgs_tags = plot_random_data(random_data, i_rnd, plot_col,
                                                 col_name, trims, borders,
                                                 compress_levels, dpis,
                                                 img_savedir, img_format,
                                                 plot_owner, imt_db)
                # now stick the new img ingo into the main dict:
                for img_file, img_info in new_imgs_tags.items():
                    images_and_tags[img_file] = img_info

        print_simple_timer(DATE_START, datetime.now(), 'plotting')
        with open(metadata_pickle, "wb") as open_pickle:
            pickle.dump(images_and_tags, open_pickle)

    # the metadata saved in images_and_tags is references to absolute
    # filepaths but it is much easier to work with a path that is relative
    # to the webdir, where the database is stored.
    # The database also does this automatically.
    #
    # In actual usage, the database would be the place to get the metadata,
    # so there is usually no need to get the metadata back from a plotting
    # process. In this test we need that information directly because we
    # want to test the integrity of the database!
    rel_images_and_tags = {}
    for img_file, img_info in images_and_tags.items():
        if img_file.startswith(webdir):
            img_file = img_file[len(webdir)+1:]
        rel_images_and_tags[img_file] = img_info
    images_and_tags = rel_images_and_tags

    # now assemble the ImageDict using the image metadata:
    img_dict = None
    # This is the simple way, but it is possible to parallelise
    # this step as done below:
    for img_file, img_info in images_and_tags.items():
        tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tagorder)
        if not img_dict:
            img_dict = imt.ImageDict(tmp_dict,
                                     selector_animated=selector_animated,
                                     animation_direction=animation_direction,
                                     level_names=sel_names_list,
                                     selector_widths=sel_widths_list)
        else:
            img_dict.append(imt.ImageDict(tmp_dict,
                                          level_names=sel_names_list))

    # Database integrity and optimisation tests:
    # Firstly, read the database. This simply loads ALL of the image metadata:
    db_imgs, db_img_tags = imt.db.read(imt_db)

    # check that the database table contains ONLY the SQLITE_IMG_INFO_TABLE
    dbcn, dbcr = imt.db.open_db_file(imt_db)
    # check for the required table:
    table_names = imt.db.list_tables(dbcr)
    dbcn.close()
    if table_names != [imt.db.SQLITE_IMG_INFO_TABLE]:
        msg = 'Database integrity failre: database contains "{}", not "{}"'
        raise ValueError(msg.format(table_names,
                                    [imt.db.SQLITE_IMG_INFO_TABLE]))

    # In this test though, we also need to verfiy the integrity of the
    # database, relative to the plotting/pickling process:
    img_list = sorted(images_and_tags.keys())
    db_imgs.sort()
    if img_list != db_imgs:
        msg = ('List of plots differ between database and '
               'plotting/pickle versions')
        raise ValueError(msg)
    if not args.skip_plotting:
        # if we have done the plotting then these should match. If not, then
        # the database delete test later on will mess this up:
        test_compare_img_tags(images_and_tags, 'plot dict',
                              db_img_tags, 'database dict')

    # For memory optimisation of large image databases, we want to make sure
    # the dictionary we get back is as small as possible in memory:
    #
    # these are the tags that we actually need to work with for the web page.
    # Others are ignored:
    required_tags = ['data source', 'number of rolls', 'plot type',
                     'plot color', 'image trim', 'border', 'expected dpi',
                     'image compression', 'SQL-char-name:in_tag']
    db_imgs, db_img_tags = imt.db.read(imt_db, required_tags=required_tags)
    # For more memory optimisation, this will return a list of all of the
    # unique metadata strings, as there is usually a lot of duplication.
    # The returned db_img_tags will then reference the strings witin
    # that list, rahter than contain the duplicated strings. This saves a
    # lot of memory for large databases of files.
    tag_strings = []
    db_imgs, db_img_tags = imt.db.read(imt_db, tag_strings=tag_strings)
    # and this both filters out un-needed tags and uses the tag_strings
    # list as a reference
    tag_strings = []
    db_imgs, db_img_tags = imt.db.read(imt_db, required_tags=required_tags,
                                       tag_strings=tag_strings)

    # test deleting a single image from the db file, and then add it back in:
    del_img = db_imgs[0]
    del_tags = db_img_tags[del_img]
    imt.db.del_plots_from_dbfile(imt_db, del_img)
    # now put it back in:
    imt.db.write_img_to_dbfile(imt_db, del_img, del_tags)
    print('Database integrity checks/memory optimsations completed')

    # Now make the next type of web page.
    # This test produces the same thing as before, but created in parallel.
    # This isn't needed for a small set of plots like this example, but the
    # code appears to scale well. For example, within the Met Office, this
    # code is used to produce internal web pages with approx 2 million images.
    n_proc = 4
    skip_key_relist = False  # default setting
    # set up a generator to break up the images into smaller chunks:
    extra_opts = (tagorder, skip_key_relist,
                  selector_animated, animation_direction)
    subdict_gen = imt.dict_split(db_img_tags,
                                 n_split=n_proc,
                                 extra_opts=extra_opts)
    if n_proc == 1:
        # this calls the processing, in series. It is much easier to debug
        # when not using the parallel calls:
        pool_out = [define_img_dict_in_tuple(x) for x in subdict_gen]
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
    print(img_dict)
    print(img_dict_para)

    # quick test of dict_index_array:
    # first to a particular depth:
    test_depth = 4
    array_inds = img_dict.dict_index_array(maxdepth=test_depth)
    # now work out how many keys there should be. This can apply in
    # this test because we have made an image for every combination of
    # keys. If that wasn't the case then the test would break. It's in
    # those cases when the img_dict.dict_index_array is useful!
    n_test_depth = 1
    for depth in range(test_depth):
        n_test_depth *= len(img_dict.keys[depth])
    if len(array_inds[1]) != n_test_depth:
        raise ValueError('Mismatch between indices to depth and keys')
    # and in full:
    array_indsf = img_dict.dict_index_array()
    if len(array_indsf[1]) != len(db_img_tags):
        raise ValueError('Mismatched indices and image array lengths')

    # now reorganise the img_dict to merge some of the images together
    # (to display multiple images side-by-side)
    #
    # This is best done after an ImageDict has been created that describes
    # all of the images, so we can use it to quickly group images together,
    # rather than having to search the long list, or the database, each time.
    # This is much quicker because the ImageDict has the same tree structure
    # that we are going to need to do the search!
    #
    # this defines the tag in the tagorder that we are grouping over.
    # It is a single integer, NOT a list as only a single tag is grouped in
    # the code below. In this case it is focusing on the plot color:
    multi_depth = tagorder.index('plot color')
    # the key_filter can be used to filter out images to go on the web page,
    # as well as report they are part of a special list for multiple images:
    # (a filter value of None means a filter is not applied,
    #  not that nothing passes the filter)
    key_filter = {'data source': None,
                  'number of rolls': img_dict.keys[tagorder.index('number of rolls')][1:],
                  'plot type': None,
                  'plot color': [img_dict.keys[multi_depth][0],
                                 ('Primary colors', img_dict.keys[multi_depth][1:]),
                                 ('All colors', img_dict.keys[multi_depth])],
                  'image trim': None,
                  'border': None,
                  'image compression': None}
    # does the multi image require that ALL of the images is
    # specifies are available, in order to present anything?
    multi_req_all = True

    # now do the work to reorganise (with a time around it):
    date_start_reorg_multi = datetime.now()


    if not args.minimal:
        # This returns a copy of the previous image dict:
        img_dict_multi = img_dict.copy_except_dict_and_keys()
        img_dict_multi.dict = {}

        # now assemble the ImageDict:
        # This is the simple way, but it is possible to parallelise this
        # step as done below:
        for img_file, img_info in images_and_tags.items():
            # test the image to see if its needed, and if it's needed
            # for the complex/multiple image case:
            img_tests = imt.simple_dict_filter(img_info, key_filter)
            # unpack the variables in img_tests:
            use_plain, use_multi, first_multi = img_tests

            if use_plain:
                # just add the image, as is:
                tmp_dict = imt.dict_heirachy_from_list(img_info,
                                                       img_file,
                                                       tagorder)
                img_dict_multi.append(imt.ImageDict(tmp_dict))

            # now we are filterig one of the levels of the dict (multi_depth)
            # by the multi_keys list:
            if use_multi and first_multi:
                for tuple_test in key_filter[tagorder[multi_depth]]:
                    if isinstance(tuple_test, tuple):
                        # split the tuple test up into meaningful variables:
                        # the name, as it will be in img_dict_multi
                        group_name = tuple_test[0]
                        # the contents that will be grouped together
                        group_values = tuple_test[1]

                        # now check that the image is the first element
                        # of this tuple_test:
                        if img_info[tagorder[multi_depth]] == group_values[0]:
                            # lookup to see if this combination has already
                            # been added to img_dict_multi, by creating a list
                            # of keys to lookup within the ImageDict:
                            key_lookup = [img_info[x] for x in tagorder]
                            key_lookup[multi_depth] = group_name

                            if len(img_dict_multi.dict) == 0:
                                already_in_img_dict_multi = False
                            else:
                                if img_dict_multi.return_from_list(key_lookup) is None:
                                    already_in_img_dict_multi = False
                                else:
                                    already_in_img_dict_multi = True

                            if already_in_img_dict_multi:
                                print('multi image already added!')
                                print(key_lookup)
                                #msg = 'Adding a multi-image that has already been added.'
                                #msg += ' Checks on first_image_multi should prevent that.'
                                #raise ValueError(msg)
                            else:
                                # this group hasn't already been added to the img_dict_multi:

                                if group_name in img_dict.keys[multi_depth]:
                                    # the group_name shouldn't be the same as
                                    # a img that identifies a single image.
                                    # That will cause problems, and will
                                    # change what is presented depening on
                                    # the order that the img_file, img_info
                                    # comes up in images_and_tags.iteritems()
                                    msg = ('A multi image group has the same img '
                                           'name as a single image')
                                    raise ValueError(msg)
                                all_img_relpaths = []

                                for this_value in group_values:
                                    # now use the key_lookup again,
                                    # only this time looking for this_value
                                    key_lookup[multi_depth] = this_value
                                    # and look in the main img_dict as that already has all
                                    # the images, sorted and easily accessible:
                                    all_img_relpaths.append(img_dict.return_from_list(key_lookup))
                                    #
                                    # If more complicated processing is required, substitutions
                                    # or fudging values, then this could be done here.

                                if multi_req_all and any([x is None for x in all_img_relpaths]):
                                    # we need all images in this list, and one fails, so just pass:
                                    pass
                                else:
                                    # now create a multi element dict, pretending to be an
                                    # image with the same properties:
                                    tmp_img_info = {}
                                    for tag_name in tagorder:
                                        tmp_img_info[tag_name] = img_info[tag_name]
                                    # with the exception of the one at multi_depth,
                                    # which is the group_name:
                                    tmp_img_info[tagorder[multi_depth]] = group_name

                                    tmp_dict = imt.dict_heirachy_from_list(tmp_img_info,
                                                                           all_img_relpaths,
                                                                           tagorder)
                                    img_dict_multi.append(imt.ImageDict(tmp_dict))

                    else:
                        # this test is a standard one, not a tuple defining a
                        # multi image, so just pass:
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
        print('reading database file: %s' % imt_db)
        dbcn, dbcr = imt.db.read_db_file_to_mem(imt_db)
        print('db file read')

        # now assemble the ImageDict:
        # This is the simple way, but it is possible to parallelise this step as done below:
        for img_file, img_info in images_and_tags.items():
            # test the image to see if its needed, and if it's
            # needed for the complex/multiple image case:
            use_plain, use_multi, first_multi = imt.simple_dict_filter(img_info, key_filter)

            if use_plain:
                # just add the image, as is:
                tmp_dict = imt.dict_heirachy_from_list(img_info, img_file, tagorder)
                img_dict_multi.append(imt.ImageDict(tmp_dict))

            # now we are filterig one of the levels of the dict (multi_depth)
            # by the multi_keys list:
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
                            key_lookup = [img_info[x] for x in tagorder]
                            key_lookup[multi_depth] = group_name

                            if len(img_dict_multi.dict) == 0:
                                already_in_img_dict_multi = False
                            else:
                                if img_dict_multi.return_from_list(key_lookup) is None:
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
                                    # the group_name shouldn't be the same as a img that identifies
                                    # a single image. That will cause problems, and will change what
                                    # is presented depening on the order that the img_file, img_info
                                    # comes up in images_and_tags.iteritems()
                                    msg = 'A multi image group has the same img name as a single image'
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
                                    # with the exception of the one at multi_depth,
                                    # which is the group_name:
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

    # delete the pre-exising javascript, to make sure it's copied over at
    # least once afresh, for testing:
    if os.path.isfile(os.path.join(webdir, 'imt_dropdown.js')):
        os.remove(os.path.join(webdir, 'imt_dropdown.js'))

    # now create a web page for each of them:
    out_page = '%s/page.html' % webdir
    out_page_para = '%s/page_para.html' % webdir

    if not args.minimal:
        out_page_multi = '%s/page_multi.html' % webdir
        # another test page, this time specifying the css:
        test_css = make_test_css(webdir)
        out_page_css = '%s/page_css.html' % webdir

    shutil.copy(LOGO_FILE, '%s/logo.png' % webdir)

    webpage_preamble = '''
<div id='logo' style='float:left;'>
  <img src=logo.png></td>
</div>
<div id='preamble'>
    <p>&nbsp;</p>
    <h1>This is a test page for the ImageMetaTag module at vn{} with python {}.</h1>
</div>
'''.format(imt.__version__, platform.python_version())

    # add a post-amble, including some server side
    #includes for last-modified, and a disk usage string.
    webpage_postamble = r'''<div id='postamble'>
  This page was last modified {}<br>
  {}
</div>
'''.format(datetime.now().strftime(DATE_FORMAT_WWW), plot_owner)

    if args.minimal:
        initial_selectors = None
    else:
        # for the test page, we want to start the page on an image that isn't the first one:
        for i_key in range(len(img_dict.keys)):
            if i_key == 0:
                # start at random:
                initial_selectors = [random.choice(img_dict.keys[i_key])]
            else:
                # select a new selector, at random, from those
                # which are consistent with the current tree:
                next_sel = random.choice(list(img_dict.return_from_list(initial_selectors).keys()))
                initial_selectors.append(next_sel)

    # on one of the pages, we'll test the ability to group selections using <optgroup>:
    # These groups are specified as a 2-level dictionary where the first level is the index
    # of the selector. The second level contains the {'group name': [contents]}
    #
    # For this test, both the color, and the compression will be grouped:
    compressions = copy.deepcopy(img_dict.keys[tagorder.index('image compression')])
    uncompressed_tags = []
    compressed_tags = []
    while compressions:
        if compressions[-1][-1] == '0':
            uncompressed_tags.append(compressions.pop())
        else:
            compressed_tags.append(compressions.pop())

    if args.minimal:
        groupings = None
    else:
        groupings = {tagorder.index('plot color'): {'Colours': ['Plotted in Red',
                                                                'Plotted in Blue',
                                                                'Plotted in Green',
                                                               ]},
                     tagorder.index('image compression'): {'Compressed': set(compressed_tags),
                                                           'Uncompressed': uncompressed_tags,
                                                           'imt_optgroup_order': ['Uncompressed',
                                                                                  'Compressed']},
                    }

    # now write out the webpages:
    web_out = {}
    web_out[out_page] = imt.webpage.write_full_page(img_dict, out_page,
                                                    'Test ImageDict webpage',
                                                    preamble=webpage_preamble,
                                                    postamble=webpage_postamble,
                                                    initial_selectors=initial_selectors,
                                                    optgroups=groupings,
                                                    verbose=True, only_show_rel_url=True,
                                                    write_intmed_tmpfile=True,
                                                    show_selector_names=True,
                                                    show_singleton_selectors=False,
                                                    compression=test_zlib_compression)

    ie_warning = "If the page does not load correctly in Internet Explorer, please try using firefox or Chrome."
    web_out[out_page_para] = imt.webpage.write_full_page(img_dict, out_page_para,
                                                         'Test ImageDict webpage (Parallel)',
                                                         preamble=webpage_preamble,
                                                         postamble=webpage_postamble,
                                                         verbose=True,
                                                         only_show_rel_url=False,
                                                         load_err_msg=ie_warning)
    if not args.minimal:
        web_out[out_page_multi] = imt.webpage.write_full_page(img_dict_multi, out_page_multi,
                                                              'Test ImageDict webpage',
                                                              preamble=webpage_preamble,
                                                              postamble=webpage_postamble,
                                                              postamble_no_imt_link=True,
                                                              last_img_in_list_is_slider=True,
                                                              verbose=True, url_type='str')
        web_out[out_page_css] = imt.webpage.write_full_page(img_dict_multi, out_page_css,
                                                            'Test ImageDict webpage with CSS',
                                                            preamble=webpage_preamble,
                                                            postamble=webpage_postamble,
                                                            verbose=True, only_show_rel_url=True,
                                                            show_selector_names=True,
                                                            last_img_in_list_is_slider=True,
                                                            last_img_still_show=True,
                                                            show_singleton_selectors=False,
                                                            compression=test_zlib_compression,
                                                            css=test_css)
    sorts_work = test_key_sorting()
    if sorts_work:
        print('Sorting tests pass OK')
    else:
        raise ValueError('Testing failed in test_key_sorting')

    if not args.minimal:

        # now, finally, produce a large ImageDict:
        if not args.no_biggus_dictus:
            print('Producing a very large ImageDict, as a scalability and speed test')
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
            n_to_do = math.factorial(9)
            n_to_do_flt = float(math.factorial(9))
            dt_prev = datetime.now()
            pcents = list(range(5, 101, 5)) # write out every 5% completed
            for i_1 in range(1):
                for i_2 in range(2):
                    for i_3 in range(3):
                        for i_4 in range(4):
                            for i_5 in range(5):
                                for i_6 in range(6):
                                    for i_7 in range(7):
                                        for i_8 in range(8):
                                            for i_9 in range(9):
                                                # we don't want to actually make an image!
                                                img_name = 'no_image_{}_{}_{}_{}_{}_{}_{}_{}_{}.png'
                                                img_name = img_name.format(i_1, i_2, i_3, i_4, i_5,
                                                                           i_6, i_7, i_8, i_9)
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
                                                    bigdb_cn, bigdb_cr = imt.db.open_or_create_db_file(bigdb,
                                                                                                       img_info,
                                                                                                       restart_db=True)
                                                    first_img = False
                                                imt.db.write_img_to_open_db(bigdb_cr, img_name, img_info)
                                                i_count += 1
                                                pcent_done = 100 * i_count / n_to_do_flt
                                                if pcent_done > pcents[0]:
                                                    dt_now = datetime.now()
                                                    msg = '{} out of {} ({:.2f}%) {}'
                                                    print(msg.format(i_count,
                                                                     n_to_do,
                                                                     pcent_done,
                                                                     dt_now - dt_prev))
                                                    dt_prev = dt_now
                                                    # remove the current percentage:
                                                    pcents.pop(0)
            print('  input dictionary complete, with %s elements' % len(biggus_dictus))

            bigdb_cn.commit()
            bigdb_cn.close()
            print_simple_timer(date_start_bigdb, datetime.now(),
                               'Producing large dictionary and database')

            # verfiy the integrity of the database, relative to biggus_dictus:
            db_imgs, db_img_tags = imt.db.read(bigdb)
            img_list = sorted(biggus_dictus.keys())
            db_imgs.sort()
            if img_list != db_imgs:
                msg = ('List of plots differ between memory and '
                       'database versions of big dict')
                raise ValueError(msg)
            if biggus_dictus != db_img_tags:
                msg = ('images_and_tags differ between memory and '
                       'database versions of big dict')
                raise ValueError(msg)

            # run through the big dict, and delete a smallish subset of
            # 'images' from the big database
            db_imgs, db_img_tags = imt.db.read(bigdb)
            len_b4_del = len(db_imgs)
            print('Length of large database before deleting subset {}'.format(len_b4_del))
            del_list = db_imgs[500::1000]
            imt.db.del_plots_from_dbfile(bigdb, del_list)

            db_imgs, db_img_tags = imt.db.read(bigdb)
            len_aft_del = len(db_imgs)
            print('Length of large database after deleting subset {}'.format(len_aft_del))
            # and check it's the right length, to see if some data is actually gone:
            if len_b4_del != len_aft_del + len(del_list):
                raise ValueError('Inconsistent database size after deleting subset.')

            # test reading only a subset of the files:
            n_samples = 500
            db_imgs, db_img_tags = imt.db.read(bigdb, n_samples=n_samples)
            len_sample = len(db_imgs)
            if len_sample != n_samples:
                raise ValueError('error loading subsample from database')
            print('Tested ability to load a random subset of images - OK')

            # now process that big dict in parallel to an ImageDict, with this tag order:
            tagorder = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8', 'l9']
            date_start_big = datetime.now()
            n_proc = 4
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

            # because we have appended to the dict without regenerating the
            # lists, so do that now:
            biggus_dictus_imigus.list_keys_by_depth()
            print_simple_timer(date_start_big, datetime.now(),
                               'Large parallel dict processing')
            # and now make we big dict webpage (and time it too)
            date_start_web = datetime.now()
            out_page_big = '%s/biggus_pageus.html' % webdir
            web_out[out_page_big] = imt.webpage.write_full_page(biggus_dictus_imigus,
                                                                out_page_big,
                                                                'Test ImageDict webpage',
                                                                compression=True)
            print_simple_timer(date_start_web, datetime.now(),
                               'Large dict webpage')

        if not args.no_db_rebuild:
            print('Testing imt.db.scan_dir_for_db')
            # rebuilding an image database from files on disk can be slow,
            # but it can be very useful in some situations:
            rebuild_db = '{}/imt_rebuild.db'.format(webdir)
            # rebuild the img_savedir, makging sure we don't scan
            # the minimal or thumbnail directory:
            imt.db.scan_dir_for_db(webdir, rebuild_db, restart_db=True,
                                   img_tag_req=required_tags,
                                   subdir_excl_list=['thumbnail', 'minimal'],
                                   known_file_tags=None, verbose=False)
            # now load that db and test it:
            imgs_r, imgs_tags_r = imt.db.read(rebuild_db,
                                              required_tags=required_tags,
                                              tag_strings=tag_strings)
            # reload the standard db:
            db_imgs, db_img_tags = imt.db.read(imt_db,
                                               required_tags=required_tags,
                                               tag_strings=tag_strings)

            if sorted(db_imgs) != sorted(imgs_r):
                raise ValueError(('Mismatch between database of plots, and '
                                  'database produced by scanning {}\n'
                                  'Has the directory got other images/old '
                                  'tests in it?').format(webdir))
            # now validate the rebuild against the standard db:
            test_compare_img_tags(imgs_tags_r, 'rebuild dict',
                                  db_img_tags, 'database dict')

            print('Testing of database rebuild functionality complete.')

    print('Web page outputs\n', web_out)

    # testing files that have known problems:
    print('testing image_file_postproc on known problem images:')
    prob_imgs = os.listdir(TEST_RESOURCES)
    for prob_img in prob_imgs:
        test_in = os.path.join(TEST_RESOURCES, prob_img)
        test_out = os.path.join(webdir, prob_img)
        print('processing {} to {}'.format(test_in, test_out))
        imt.image_file_postproc(test_in, outfile=test_out,
                                img_tags={'test': 'value'})

    print('test.py completed')

if __name__ == '__main__':
    __main__()
