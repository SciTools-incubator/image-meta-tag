'''
This sub-module contains functions to write out an :class:`ImageMetaTag.ImageDict` to a webpage.

The webpages are made up of a single .html file, which is the page to be loaded to view the images.
Alongside this is a short ImageMetaTag javascript library held in a '.js' file
(currently held in a single file) and a .json file contain the :class:`ImageMetaTag.ImageDict`
tree strcuture as a JSON data strcuture.

To reduce file size, the JSON data structure can be compressed using zlib. If this is the case,
then the `pako javascript library <https://github.com/nodeca/pako>`_ is used restore the JSON
data in the browser.

This can either be done using write_full_page, to produce a page with just a set of
selectors to browse the ImageDict, or the different components can be added to a
page as it is being constructed (reading in an html template, for instance).

To write out a full page, use :func:`ImageMetaTag.webpage.write_full_page`.

If the latter, then the following sections are needed:

    * :func:`ImageMetaTag.webpage.write_js_to_header` - writes out the javascript information\
                                                to the html header
    * :func:`ImageMetaTag.webpage.write_js_placeholders` - writes out the placeholders that\
                                                        the javascript will write images to.
    * :func:`ImageMetaTag.webpage.write_json` - writes out the :class:`ImageMetaTag.ImageDict`\
                                                as a json.dump to a json file
    * :func:`ImageMetaTag.webpage.copy_required_javascript` - copies required javascript library \
                                                          to the required location.

An easy example of creating a webpage, using an :class:`ImageMetaTag.ImageDict` is shown in
`simplest_image_dict.py <simple.html>`_

.. TIP:: At present, the only webpage style that can be produced is a set of horizontal dropdown\
menus, but more will hopefully be added soon.

.. moduleauthor:: Melissa Brooks https://github.com/melissaebrooks

(C) Crown copyright Met Office. All rights reserved.
Released under BSD 3-Clause License. See LICENSE for more details.
'''

import os, json, pdb, shutil, tempfile, copy, zlib
import numpy as np
import ImageMetaTag as imt

from multiprocessing import Pool

# single indent to be used on the output webpage
INDENT = '  '
LEN_INDENT = len(INDENT)


# for compressed json files, we use pako to inflate the data back to full size:
PAKO_JS_FILE = 'pako_inflate.js'
PAKO_RELEASE = '1.0.5'
PAKO_SOURCE_TAR = 'https://github.com/nodeca/pako/archive/{}.tar.gz'.format(PAKO_RELEASE)


def write_full_page(img_dict, filepath, title, page_filename=None, tab_s_name=None,
                    preamble=None, postamble=None, postamble_no_imt_link=False,
                    compression=False,
                    initial_selectors=None, show_selector_names=False,
                    show_singleton_selectors=True, optgroups=None,
                    url_type='int', only_show_rel_url=False, verbose=False,
                    style='horiz dropdowns', write_intmed_tmpfile=False,
                    description=None, keywords=None, css=None, load_err_msg=None):
    '''
    Writes out an :class:`ImageMetaTag.ImageDict` as a webpage, to a given file location.
    The files are created as temporary files and when complete they replace any files that
    are currently in the specified location.

    If the img_dict supplied is None, rather than the appropriate class, then a page will
    be produced with the image selectors missing, and a message saying no images are available.

    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.

    Options:

     * page_filename - the file name, within the directory (defaults to the name of the file) \
                       but can be set if tab_s_name is also used.
     * tab_s_name : used to denote the name of the page, when it is used as a frame \
                    of a larger page.
     * preamble : html text added at the top of the <body> text, but before the ImageMetaTag \
                  section. Can be quite extensive.
     * postable : html text added after the ImageMetaTag section. A link to the ImageMetaTag \
                  documentation will be appended unless postamble_no_imt_link is True.
     * postamble_no_imt_link : if True, no link to the ImageMetaTag documentation will be added \
                               to the postamble.
     * initial_selectors - A list of initial values for the selectors, to be passed into \
                           :func:`ImageMetaTag.webpage.write_js_setup`.
     * show_selector_names - switches on displaying the selector full names defined by the \
                             :class:`ImageMetaTag.ImageDict`.full_name_mapping
     * show_singleton_selectors - When set to False, selectors that have only one element are \
                                 not displayed (default=True).
     * optgroups - The contents of selectors can be grouped together to make large lists \
                   more readable. This is passed into \
                   :func:`ImageMetaTag.webpage.write_js_to_header`.
     * url_type - determines the type of URL at the bottom of the ImageMetaTag section. Can be \
                  'int' or 'str'.
     * only_show_rel_url - If True, the wepage will only show relative urls in is link section.
     * verbose - If True, stdout will be more verbose
     * style - the style of output page to write, currently only 'horiz dropdowns' is valid
     * write_intmed_tmpfile - If True, files are written out to temporary filenames and then \
                              moved when completed.
     * description - html description metadata
     * keywords - html keyword metadata
     * compression - default False. If True, then the json data object will be compressed \
                     using zlib string compression. When read into the browser, we will use \
                     pako to inflate it (https://github.com/nodeca/pako)
     * css - Optional CSS file used to style webpage. By default a small amount of css is \
             written out in the page header.
     * load_err_msg - additional message to show after 'Please wait while the page is loading'. \
                      default is None, but very large pages can crash with Internet Explorer so \
                      a message along the lines of this may be useful: 'If the page does not \
                      load correctly in Internet Explorer, please try using firefox or Chrome.'

    Returns a list of files that the the created webpage is dependent upon.

    '''

    page_dependencies = []

    if not (isinstance(img_dict, imt.ImageDict) or img_dict is None):
        raise ValueError('write_full_page works on an ImageMetaTag ImageDict.')

    if page_filename is None:
        page_filename = os.path.basename(filepath)
    if not page_filename:
        msg = 'filepath ({})" must specify a file (not a directory'
        raise ValueError(msg.format(filepath))

    # other files involved:
    file_dir, file_name = os.path.split(filepath)
    page_dependencies.append(file_name)

    if img_dict is None:
        json_files = []
    else:
        # now make sure the required javascript library is copied over to the file_dir:
        js_files = copy_required_javascript(file_dir, style, compression=compression)
        page_dependencies.extend(js_files)

        # we have real data to work with:
        # this tests the dict has uniform_depth, which is needed for all current webpages.
        dict_depth = img_dict.dict_depth(uniform_depth=True)
        # work out what files we need to create:
        file_name_no_ext = os.path.splitext(file_name)[0]
        # json file to hold the image_dict branching data etc:
        json_file_no_ext = os.path.join(file_dir, file_name_no_ext)
        json_files = write_json(img_dict, json_file_no_ext, compression=compression)
        # the final page is dependent on the final locations of the json files,
        # relative to the html:
        page_dependencies.extend([os.path.split(x[1])[1] for x in json_files])

        # this is the internal name the different selectors, associated lists for the selectors, and
        # the list of files (all with a numbered suffix):
        selector_prefix = 'sel'
        url_separator = '|'

    # now write the actual output file:
    if write_intmed_tmpfile:
        # get a temporary file:
        with tempfile.NamedTemporaryFile('w', suffix='.html', prefix='imt_tmppage_',
                                         dir=file_dir, delete=False) as html_file_obj:
            tmp_html_filepath = html_file_obj.name
        filepath_to_write = tmp_html_filepath
    else:
        filepath_to_write = filepath
    # start the indent:
    ind = ''

    # open the file - this is a nice and simple file so just use the with open...
    with open(filepath_to_write, 'w') as out_file:
        # write out the start of the file:
        out_file.write('<!DOCTYPE html>\n')
        out_file.write(ind + '<html>\n')
        # increase the indent level:
        ind = _indent_up_one(ind)
        out_file.write(ind + '<head>\n')
        ind = _indent_up_one(ind)
        if title is not None:
            out_file.write('{}<title>{}</title>\n'.format(ind, title))
        out_str = ind+'<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">\n'
        out_file.write(out_str)

        if css:
            # copy the css file into the file_dir (unless that's were it already is):
            try:
                shutil.copy(css, file_dir)
            except shutil.Error as sh_err:
                if imt.PY3:
                    if 'are the same file' in sh_err.__str__():
                        pass
                    else:
                        raise sh_err
                else:
                    if 'are the same file' in sh_err.message:
                        pass
                    else:
                        raise sh_err
            base_css = os.path.basename(css)
            page_dependencies.append(base_css)
            out_str = ind+'<link rel="stylesheet" type="text/css" href="{0}">\n'
            out_file.write(out_str.format(base_css))

        else:
            if style == 'horiz dropdowns':
                # write out a little css at the top:
                css = '''{0}<style>
{0}  body {{
{0}    background-color: #ffffff;
{0}    color: #000000;
{0}  }}
{0}  body, div, dl, dt, dd, li, h1, h2 {{
{0}    margin: 0;
{0}    padding: 0;
{0}  }}
{0}  h3, h4, h5, h6, pre, form, fieldset, input {{'
{0}    margin: 0;
{0}    padding: 0;
{0}  }}
{0}  textarea, p, blockquote {{
{0}    margin: 0;
{0}   padding: 0;
{0}  }}
{0}  th, td {{
{0}    margin: 0;
{0}    padding: 0;
{0}    vertical-align: top;
{0}  }}
{0}  fieldset, img {{
{0}    border: 0 none;
{0}    vertical-align: top;
{0}  }}
{0}  body {{
{0}    font: 12px Myriad,Helvetica,Tahoma,Arial,clean,sans-serif;
{0}    *font-size: 75%;
{0}  }}
{0}  h1 {{
{0}    font-size: 1.5em;
{0}    font-weight: normal;
{0}    line-height: 1em;
{0}    margin-top: 1em;
{0}    margin-bottom:0;
{0}  }}
{0}  h2 {{
{0}    font-size: 1.1667em;
{0}    font-weight: bold;
{0}    line-height: 1.286em;
{0}    margin-top: 1.929em;
{0}    margin-bottom:0.643em;
{0}  }}
{0}  h3, h4, h5, h6 {{
{0}    font-size: 1em;
{0}    font-weight: bold;
{0}    line-height: 1.5em;
{0}    margin-top: 1.5em;
{0}    margin-bottom: 0;
{0}  }}
{0}  p {{
{0}    font-size: 1em;
{0}    margin-top: 1.5em;
{0}    margin-bottom: 1.5em;
{0}    line-height: 1.5em;
{0}  }}
{0}  pre, code {{
{0}    font-size:115%;
{0}    *font-size:100%;
{0}    font-family: Courier, "Courier New";
{0}    background-color: #efefef;
{0}    border: 1px solid #ccc;
{0}  }}
{0}  pre {{
{0}    border-width: 1px 0;
{0}    padding: 1.5em;
{0}  }}
{0}  table {{
{0}    font-size:100%;
{0}  }}
{0}</style>
'''
                out_file.write(css.format(ind))

        # now write out the specific stuff to the html header:
        if img_dict is None:
            # an empty img_dict needs very little:
            write_js_to_header(img_dict,
                               file_obj=out_file,
                               pagename=page_filename, tabname=tab_s_name,
                               ind=ind,
                               description=description, keywords=keywords)
        else:
            # the json_files is a list of (tmp_file, final_file) tuples.
            # Here we want the final one:
            final_json_files = [os.path.split(x[1])[1] for x in json_files]
            write_js_to_header(img_dict, initial_selectors=initial_selectors, optgroups=optgroups,
                               file_obj=out_file, json_files=final_json_files, js_files=js_files,
                               pagename=page_filename, tabname=tab_s_name,
                               selector_prefix=selector_prefix, url_separator=url_separator,
                               show_singleton_selectors=show_singleton_selectors,
                               url_type=url_type, only_show_rel_url=only_show_rel_url,
                               style=style, ind=ind, compression=compression,
                               description=description, keywords=keywords)
        # now close the script and head:
        ind = _indent_down_one(ind)
        out_file.write(ind + '</script>\n')
        ind = _indent_down_one(ind)
        out_file.write(ind + '</head>\n')

        # now start the body:
        out_file.write('{}<body>\n'.format(ind))

        # the preamble is the first thing to go in the body:
        if preamble is not None:
            out_file.write(preamble + '\n')
        # now the img_dict content:
        if img_dict is None:
            out_file.write('<p><h1>No images are available for this page.</h1></p>')
        else:
            # now write out the end, which includes the placeholders for the actual
            # stuff that appears on the page:
            if show_selector_names:
                level_names = img_dict.level_names
            else:
                level_names = False
            # if we're labelling selectors, and we have an animator button, label that too:
            if img_dict.selector_animated > 1 and show_selector_names:
                anim_level = level_names[img_dict.selector_animated]
            else:
                anim_level = None
            write_js_placeholders(img_dict, file_obj=out_file, dict_depth=img_dict.dict_depth(),
                                  style=style, level_names=level_names,
                                  show_singleton_selectors=show_singleton_selectors,
                                  animated_level=anim_level, load_err_msg=load_err_msg)

        # the body is done, so the postamble comes in:
        postamble_endline = 'Page created with <a href="{}">ImageMetaTag {}</a>'
        postamble_endline = postamble_endline.format(imt.__documentation__, imt.__version__)
        if not postamble_no_imt_link:
            if postamble is None:
                postamble = postamble_endline
            else:
                postamble = '{}\n{}'.format(postamble, postamble_endline)
        if postamble is not None:
            out_file.write(postamble + '\n')
        # finish the body, and html:
        out_file.write(ind + '</body>\n')
        out_file.write('\n</html>')

        if write_intmed_tmpfile:
            tmp_files_to_mv = json_files + [(tmp_html_filepath, filepath)]
        else:
            tmp_files_to_mv = json_files
        for tmp_file_mv in tmp_files_to_mv:
            # now move the json, then the html files:
            os.chmod(tmp_file_mv[0], 0o644)
            shutil.move(tmp_file_mv[0], tmp_file_mv[1])

        if verbose:
            print('File "%s" complete.' % filepath)

    return page_dependencies

def write_js_to_header(img_dict, initial_selectors=None, optgroups=None, style=None,
                       file_obj=None, json_files=None, js_files=None,
                       pagename=None, tabname=None, selector_prefix=None,
                       show_singleton_selectors=True,
                       url_separator='|', url_type='str', only_show_rel_url=False,
                       ind=None, compression=False,
                       description=None, keywords=None):
    '''
    Writes out the required ImageMetaTag config and data paths into a html header section
    for an input :class:`ImageMetaTag.ImageDict`.

    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.

    * initial_selectors - A list of initial values for the selectors.
    * optgroups - The contents of selectors can be grouped together to make large lists \
                  more readable. These groups are specified as a 2-level dictionary where the \
                  first level is the index of the selectors to have groups. \
                  The second level contains the {'group name': [contents]}.
                  By specifying an optgroup, the order of the elements in a selector uses \
                  the optgroups first. By default the optgroup names are sorted, but the \
                  order of the optgroups can be specified by including a \
                     'imt_optgroup_order': [ordered list of opgroup names],
                  in a second level dictionary that specifies the 'group name': [contents] \
                  Within each optgroup the order of elements is taken from their order in the \
                  image dict.
    * style - the style of the output webpage, currently only 'horiz dropdowns' is available
    * file_obj - the open file object to write the header to.
    * json_files - a list of the json (or other similar object) containing the representation of \
                  the ImageDict data.
    * js_file - the javascript file containing the actual scripting for the selected style.
    * pagename - the file name, within the directory (defaults to the name of the file) \
                 but can be set if tab_s_name is also used.
    * tabname : used to denote the name of the page, when it is used as a frame \
                of a larger page.
    * selector_prefix - prefix to use for javascript selector names (defaults to 'sel')
    * show_singleton_selectors - When set to False, selectors that have only one element are \
                                not displayed (default=True).
    * url_type - determines the type of URL at the bottom of the ImageMetaTag section. Can be \
                 'int' or 'str'.
    * only_show_rel_url - If True, the wepage will only show relative urls in is link section.
    * ind - indentation going into the header section.
    * compression - Indicates the json file is compressed using zlib.
    * description - html description metadata7
    * keywords - html keyword metadata
    '''
    if not (isinstance(img_dict, imt.ImageDict) or img_dict is None):
        raise ValueError('Input img_dict is not an ImageMetaTag ImageDict')

    if ind is None:
        ind = ''

    if description is not None:
        file_obj.write('{}<meta name="description" content="{}">\n'.format(ind, description))
    if keywords is not None:
        file_obj.write('{}<meta name="keywords" content="{}">\n'.format(ind, keywords))

    if img_dict is not None:
        ## add a reference to the data structure:
        #out_str = '{}<script type="text/javascript" src="{}"></script>\n'.format(ind, json_files)
        #file_obj.write(out_str)

        # now add a reference to the javascript functions to implement the style:
        for js_file in js_files:
            out_str = '{}<script type="text/javascript" src="{}"></script>\n'.format(ind, js_file)
            file_obj.write(out_str)

        # now write out the javascript configuration variables:
        file_obj.write(ind + '<script type="text/javascript">\n')
        ind = _indent_up_one(ind)
        # define, read in and parse the json file:
        out_str = '''{0}var json_files = {1};
{0}var zl_unpack = {2};
{0}imt = read_parse_json_files(json_files, zl_unpack);
'''
        file_obj.write(out_str.format(ind, json_files, _py_to_js_bool(bool(compression))))

        # in case the page we are writing is embedded as a frame, write out the top
        # level page here;
        file_obj.write('{}var pagename = "{}"\n'.format(ind, pagename))
        # the tab name is used in setting up the URL in nested frames:
        file_obj.write('{}var tab_name = "{}";\n'.format(ind, tabname))

        dict_depth = img_dict.dict_depth()
        # the key_to_selector variable is what maps each set of keys onto a selector on the page:
        key_to_selector = str([selector_prefix + str(x) for x in range(dict_depth)])
        file_obj.write('{}var key_to_selector = {};\n'.format(ind, key_to_selector))
        # this determines whether a selector uses the animation controls on a page:
        file_obj.write('{}var anim_sel = {};\n'.format(ind, img_dict.selector_animated))
        # and the direction the animation runs in:
        file_obj.write('{}var anim_dir = {};\n'.format(ind, img_dict.animation_direction))
        # and the direction the animation runs in:

        # the url_separator is the text character that goes between the variables in the url:
        if url_separator == '&':
            msg = 'Cannot use "&" as the url_separator, as some strings will '
            msg += 'become html special characters. For instance &para-global '
            msg += 'will be treated as a paragraph then -global, not the intended string.'
            raise ValueError(msg)
        file_obj.write('{}var url_separator = "{}";\n'.format(ind, url_separator))

        # the url_type determines whether the url is full of integers (int), with meaningful
        # values internally or text which looks more meaningful to the user:
        file_obj.write('{}var url_type = "{}";\n'.format(ind, url_type))
        # the show_rel_url logical (converted to a string to init a javascript bool)
        file_obj.write('{}var show_rel_url = {};\n'.format(ind, _py_to_js_bool(only_show_rel_url)))

        # the selected_id needs to be defined here too, as it's used as a global variable
        # (it will be overwritten later if the URL changes it, and when selectors change it):
        if initial_selectors is None:
            # if it's not set, then set it to something invalid, and the validator
            # in the javascript will sort it out. It MUST be the right length though:
            file_obj.write('{}var selected_id = {};\n'.format(ind, str([-1]*dict_depth)))
        else:
            if not isinstance(initial_selectors, list):
                msg = 'Input initial_selectors must be a list, of length the depth of the ImageDict'
                raise ValueError(msg)
            if len(initial_selectors) != img_dict.dict_depth():
                msg = 'Input initial_selectors must be a list, of length the depth of the ImageDict'
                raise ValueError(msg)
            # the input can either be a list of integer indices, or strings that match:
            initial_selectors_as_inds = []
            initial_selectors_as_string = []
            for i_sel, sel_value in enumerate(initial_selectors):
                if isinstance(sel_value, int):
                    if sel_value < 0 or sel_value >= len(img_dict.keys[i_sel]):
                        raise ValueError('initial_selectors are out of range')
                    # store the initial_selectors_as_inds
                    initial_selectors_as_inds.append(sel_value)
                    # and as a string:
                    initial_selectors_as_string.append(img_dict.keys[i_sel][sel_value])
                else:
                    # get the index of that value:
                    initial_selectors_as_inds.append(img_dict.keys[i_sel].index(sel_value))
                    # and simple store the string:
                    initial_selectors_as_string.append(sel_value)
            # check that's valid:
            if img_dict.return_from_list(initial_selectors_as_string) is None:
                raise ValueError('Input initial_selectors does not end up at a valid image/payload')
            # write that out:
            file_obj.write('{}var selected_id = {};\n'.format(ind, initial_selectors_as_inds))

        # now write out the lists of keys, to the different levels:
        keys_to_js = [str(x[1]) for x in img_dict.keys.items()]
        file_obj.write('{}var key_lists = [{},\n'.format(ind, keys_to_js[0]))
        ind = _indent_up_one(ind)
        for i_depth in range(1, dict_depth):
            file_obj.write('{}{},\n'.format(ind, keys_to_js[i_depth]))
        ind = _indent_down_one(ind)
        file_obj.write(ind + '];\n')

        # now write out optgroups:
        non_optgroup_elems = {}
        if optgroups:
            # if the optgroup order hasn't been specified, then
            # the default is a sort:
            for group_ind, optgroup in optgroups.items():
                # keep a note of the elements in the whole list, so we know which ones
                # aren't in any optgroup:
                all_keys = copy.deepcopy(img_dict.keys[group_ind])
                if 'imt_optgroup_order' not in optgroup:
                    optgroup['imt_optgroup_order'] = sorted(optgroup.keys())
                # make sure that the elements within the optgroup are a sorted
                # list, sorted according to the order in the img_dict.keys()
                for group_name, group_elements in optgroup.items():
                    if group_name != 'imt_optgroup_order':
                        # pick up the indices of the elements, in the main list of keys:
                        elem_inds = [img_dict.keys[group_ind].index(x) for x in group_elements]
                        # now sort by elem_inds
                        sorted_elems = sorted(zip(elem_inds, group_elements))
                        # and pull out the bit we need again:
                        optgroup[group_name] = [x[1] for x in sorted_elems]

                        # and make a list of those elements that aren't in any optgroup!
                        for group_element in group_elements:
                            all_keys.remove(group_element)
                non_optgroup_elems[group_ind] = all_keys

            # convert the optgroups to a list, in javascript, with each selector
            # having an element within it:
            optg_str = '['
            non_optg_str = '['
            for i_depth in range(dict_depth):
                if i_depth in optgroups:
                    optg_str += json.dumps(optgroups[i_depth], separators=(',', ':'))
                    non_optg_str += str(non_optgroup_elems[i_depth])
                else:
                    # no optgroup for this selector:
                    optg_str += '{}'
                    non_optg_str += '[]'
                if i_depth < dict_depth -1:
                    # the final element mustn't have a comma or internet explorer will complain:
                    optg_str += ','
                    non_optg_str += ','
            # close the javascript list:
            optg_str += '];'
            non_optg_str += '];'
        else:
            optg_str = '[' + '{},' * (dict_depth-1) + '{}]'
            non_optg_str = '[' + '[],' * (dict_depth-1) + '[]]'
        file_obj.write('{}var optgroups = {}\n'.format(ind, optg_str))
        file_obj.write('{}var optgroup_redisual = {}\n'.format(ind, non_optg_str))
        file_obj.write('{}var show_singleton_selectors = {};\n'.format(ind, int(show_singleton_selectors)))

        # now some top level things:
        if style == 'horiz dropdowns':
            file_obj.write('''
{0}// other top level derived variables
{0}// the depth of the ImageMetaTag ImageDict (number of selectors):
{0}var n_deep = selected_id.length;
{0}// a list of the options available to the animator buttons, with the current selection
{0}var anim_options = [];
{0}// the index of the current option for the animator:
{0}var anim_ind = 0;
'''.format(ind))

        # now, the main call:
        file_obj.write(ind + '// redefine onload, so it calls the imt_main to write the page:\n')
        file_obj.write(ind + 'window.onload = function() {imt_main();}\n')
        # END of the imt specifc header content:

def write_js_setup_defaults(selector_prefix=None, list_prefix=None, file_list_name=None):
    '''
    this specifies defaults for the internal names the different selectors, associated lists for
    the selectors, and the list of files (all with a numbered suffix)
    '''
    if selector_prefix is None:
        selector_prefix = 'sel'
    if list_prefix is None:
        list_prefix = 'list'
    if file_list_name is None:
        file_list_name = 'file_list'
    return (selector_prefix, list_prefix, file_list_name)

def write_json(img_dict, file_name_no_ext, compression=False,
               chunk_char_limit=1e7):
    '''
    Writes a json dump of the :class:`ImageMetaTag.ImageDict` tree strucuture
    to a target file path.

    Options:
     * compression : If True, json is compressed using zlib compresion
     * chunk_char_limit : large strings are split into chunks for memory efficency \
                          in the browser.

    Returns a list of json files as (tempfile, final_file) tuples.
    '''

    def json_from_dict(in_dict):
        'returns a json string from an input dict'
        return json.dumps(in_dict, separators=(',', ':'))

    if isinstance(img_dict, imt.ImageDict):
        dict_as_json = json_from_dict(img_dict.dict)
    elif isinstance(img_dict, str):
        dict_as_json = img_dict
    else:
        raise ValueError('input img_dict is not an ImageMetaTag.ImageDict or string')

    # file suffix:
    suffix = '.json'
    if compression:
        suffix += '.zlib'

    # the output files:
    out_files = []

    tmp_file_dir = os.path.split(file_name_no_ext)[0]

    # use the maximum length of a single string per file:
    n_chunks = np.ceil(len(dict_as_json) / chunk_char_limit)
    n_chunks = int(n_chunks)

    if n_chunks == 1:
        # easy if it fits into a single file:
        json_file = file_name_no_ext + suffix
        if compression:
            wrt_str, file_mode = compress_string(dict_as_json)
        else:
            wrt_str = dict_as_json
            file_mode = 'w'
        with tempfile.NamedTemporaryFile(file_mode, suffix='.json', prefix='imt_',
                                         dir=tmp_file_dir, delete=False) as file_obj:
            file_obj.write(wrt_str)
            tmp_file_path = file_obj.name
        # make a note of the outputs:
        out_files.append((tmp_file_path, json_file))
    else:
        # find the appropriate depth at which to split the dict:
        if not isinstance(img_dict, imt.ImageDict):
            msg = 'Large data sets need to be supplied as an ImageDict, so they can be split'
            raise ValueError(msg)
        dict_depth = img_dict.dict_depth(uniform_depth=True)
        if len(img_dict.keys) != dict_depth:
            raise ValueError('Inconsistent depth and keys. Do the keys need relisting?')

        # determine approximately how many splits will be obtained by breaking up the
        # dictionary at each level, assuming the tree structure branches uniformly.
        n_by_depth = []
        for i_depth in range(dict_depth):
            if i_depth == 0:
                n_by_depth = [len(img_dict.keys[i_depth])]
            else:
                n_by_depth.append(len(img_dict.keys[i_depth]) * n_by_depth[-1])
            if n_by_depth[-1] >= n_chunks:
                break
        # i_depth is an index, but depth is the number of levels, so needs one adding:
        depth = i_depth + 1
        # get all the combinations of keys that reach the required depth:
        keys, array_inds = img_dict.dict_index_array(maxdepth=depth)

        # now loop through the array_inds. Each one contains the indices of a valid path through
        # the dict, to the required depth. Each subdict will be written to a separate .json file
        paths = []
        top_dict = {}
        for i_json, path_inds in enumerate(array_inds):
            # traverse to the subdict, given by the current path,
            # storing the keys of the path along the way
            subdict = img_dict.dict
            path = []
            for level, ind in enumerate(path_inds):
                subdict = subdict[keys[level][ind]]
                path.append(keys[level][ind])

            # convert the subdict to .json
            subdict_as_json = json_from_dict(subdict)
            # and write this out:
            json_file = '{}_{}{}'.format(file_name_no_ext, i_json, suffix)
            if compression:
                wrt_str, file_mode = compress_string(subdict_as_json)
            else:
                wrt_str = dict_as_json
                file_mode = 'w'
            with tempfile.NamedTemporaryFile(file_mode, suffix='.json', prefix='imt_',
                                             dir=tmp_file_dir, delete=False) as file_obj:
                file_obj.write(wrt_str)
                tmp_file_path = file_obj.name
            # make a note of the outputs:
            out_files.append((tmp_file_path, json_file))

            # now add this to the top level dict structure, so the final
            # json file can pull them all togther:
            path_dict = {path[-1]: '**FILE_{}**'.format(i_json)}
            # go backwards, from the second from last element of the path, to add more;
            for key in path[-2::-1]:
                path_dict = {key: path_dict}
            img_dict.dict_union(top_dict, path_dict)
            # add it to the paths, as a cross reference:
            paths.append(path)

        # now create the final json file that combines the previous
        # ones into a single usable object:
        i_json += 1
        # convert the subdict to .json
        subdict_as_json = json_from_dict(top_dict)
        # and write this out:
        json_file = '{}_{}{}'.format(file_name_no_ext, i_json, suffix)
        if compression:
            wrt_str, file_mode = compress_string(subdict_as_json)
        else:
            wrt_str = dict_as_json
            file_mode = 'w'
        with tempfile.NamedTemporaryFile(file_mode, suffix='.json', prefix='imt_',
                                         dir=tmp_file_dir, delete=False) as file_obj:
            file_obj.write(wrt_str)
            tmp_file_path = file_obj.name
        # make a note of the outputs:
        out_files.append((tmp_file_path, json_file))

    return out_files

def compress_string(in_str):
    '''
    Compresses a string using zlib to a format that can be read with pako.
    Returns both the compressed string and the file mode to use.
    '''
    if imt.PY3:
        # python3, compress a byte:
        #comp_str = str(zlib.compress(bytearray(in_str, 'utf-8')))
        comp_str = zlib.compress(in_str.encode(encoding='utf=8'))
        file_mode = 'wb'
    else:
        # python2, compress a string:
        comp_str = zlib.compress(in_str)
        file_mode = 'w'
    return comp_str, file_mode

def write_js_placeholders(img_dict, file_obj=None, dict_depth=None,
                          selector_prefix=None,
                          style='horiz dropdowns', level_names=False,
                          show_singleton_selectors=True,
                          animated_level=None, load_err_msg=None):
    '''
    Writes the placeholders into the page body, for the javascript to
    manipulate

     * file_obj - an open file object to write to
     * dict_dept - the depth of the :class:`ImageMetaTag.ImageDict` \
                   being written
     * selector_prefix - prefix for the variable names of the selectors \
                        (these are visible to people viewing the webpage!)
     * style - In future, it would be great to write out different types of \
               webpages. For now they are always horizontal dropdown menus.
     * show_singleton_selectors - When set to False, selectors that have \
                                  only one element are not displayed \
                                  (default=True).
     * level_names - if supplied, this need to be a list of full names, for \
                     the selectors, of length dict_depth.
     * animated_level - if supplied, as a string, this will be used to label \
                        the animator buttons.
     * load_err_msg - additional message to show after 'Please wait while the \
                      page is loading'. default is None, but very large pages \
                      can crash with Internet Explorer so a message along the \
                      lines of this may be useful: 'If the page does not load \
                      correctly in Internet Explorer, please try using \
                      firefox or Chrome.'
    '''

    if not show_singleton_selectors:
        # work out which selectors we actually want to show:
        show_sel = [len(img_dict.keys[x]) > 1 for x in range(dict_depth)]
        if not any(show_sel):
            # if there aren't any selectors in this way, that's usually a mistake
            # so show them all:
            show_sel = [True] * dict_depth
    else:
        show_sel = [True] * dict_depth
    sels_shown = sum(show_sel)

    if selector_prefix is None:
        selector_prefix, _junk1, _junk2 = write_js_setup_defaults()

    apply_level_names = False
    if level_names:
        if not isinstance(level_names, list):
            raise ValueError('level_names needs to be a list of length dict_depth')
        if len(level_names) != dict_depth:
            raise ValueError('level_names needs to be a list, of length dict_depth')
        apply_level_names = True
    else:
        apply_level_names = False

    if style == 'horiz dropdowns':
        file_obj.write('''
<!-- Now for some placeholders for the scripts to put content -->
<table border=0 cellspacing=0 cellpadding=0 width=99% align=center>
 <tr>
  <td>
   <font size=3>''')
        # a text label for the animator buttons:
        if isinstance(animated_level, str):
            anim_label = '{}: '.format(animated_level)
        else:
            anim_label = ''

        # for each level of depth in the plot dictionary, add a span to hold the selector:
        if apply_level_names:
            # if we want labelled selectors, then write out
            # a table, with pairs of label, selector, in columns:
            file_obj.write('''
   <table border=0 cellspacing=0 cellpadding=0 style='border-spacing: 3px 0;'>
     <tr>
''')
            for level in range(dict_depth):
                if show_sel[level]:
                    file_obj.write('       <td>{}&nbsp;&nbsp;</td>\n'.format(level_names[level]))
            file_obj.write('''     </tr>
     <tr>
''')
            for level in range(dict_depth):
                if show_sel[level]:
                    selp = selector_prefix + str(level)
                    out_str = '       <td><span id="{}">&nbsp;</span></td>\n'.format(selp)
                    file_obj.write(out_str)
            file_obj.write('''     </tr>
''')
            # add the placeholder for animators buttons:
            file_obj.write('''     <tr>
      <td colspan={}>
        {}<span id="animator1">&nbsp;</span>
        <span id="animator2">&nbsp;</span>
      </td>
    </tr>
   </table>
'''.format(dict_depth, anim_label))
        else:
            # simply a set of spans, in a line:
            for lev in range(dict_depth):
                if show_sel[lev]:
                    file_obj.write('''
   <span id="%s%s">&nbsp;</span>''' % (selector_prefix, lev))
            file_obj.write('\n   <br>')
            # add the placeholder for animators buttons:
            file_obj.write('''
   {}<span id="animator1">&nbsp;</span>
   <span id="animator2">&nbsp;</span>
   <br>
'''.format(anim_label))

        # now add somewhere for the image to go:
        if load_err_msg is None:
            img_div = '   <div id="the_image">Please wait while the page is loading</div>'
            file_obj.write(img_div)
        else:
            img_div = '   <div id="the_image">Please wait while the page is loading.<br>{}</div>'
            file_obj.write(img_div.format(load_err_msg))
        file_obj.write('\n   <div id="the_url">....</div>')
        # and finish off the placeholders:
        file_obj.write('''
   </font>
  </td>
 </tr>
</table>

''')

    else:
        raise ValueError('"%s" tyle of content placeholder not defined' % style)

def copy_required_javascript(file_dir, style, compression=False, overwrite=True):
    '''
    Copies the required javascript library to the directory
    containing the required page (file_dir) for a given webpage style.

    If a file is already present it will be checked based it's first line.
    If the file is different, it will be overwritten if overwrite is True.

    Also copies/obtains required javascript for reading files compressed
    with zlib, if compression=True.
    '''

    if style == 'horiz dropdowns':
        imt_js_to_copy = 'imt_dropdown.js'
        # get this from the installed ImageMetaTag directory:
        file_src_dir = os.path.join(imt.__path__[0], 'javascript')
        first_line = '// ImageMetaTag dropdown menu scripting - vn{}\n'.format(imt.__version__)
    else:
        raise ValueError('Javascript library not set up for style: {}'.format(style))

    if not os.path.isfile(os.path.join(file_dir, imt_js_to_copy)):
        # file isn't in target dir, so copy it:
        shutil.copy(os.path.join(file_src_dir, imt_js_to_copy),
                    os.path.join(file_dir, imt_js_to_copy))
    else:
        # the file is there, check it's right:
        with open(os.path.join(file_dir, imt_js_to_copy)) as file_obj:
            this_first_line = file_obj.readline()
        if first_line == this_first_line:
            # the file is good, move on:
            pass
        else:
            if overwrite:
                shutil.copy(os.path.join(file_src_dir, imt_js_to_copy),
                            os.path.join(file_dir, imt_js_to_copy))
            else:
                print('''File: {}/{} differs to the expected contents, but is
not being overwritten. Your webpage may be broken!'''.format(file_dir, imt_js_to_copy))

    # make a list of all the required javascript files
    js_files = [imt_js_to_copy]

    # now move on to javascript dependencies from the compression:
    if compression:
        js_to_copy = PAKO_JS_FILE

        js_src = os.path.join(file_src_dir, js_to_copy)
        js_dest = os.path.join(file_dir, js_to_copy)
        # if the file is already at destination, we're good:
        if os.path.isfile(js_dest):
            pass
        else:
            # is the required file in the javascript source directory:
            if not os.path.isfile(js_src):
                # we need to get the required javascript from source.
                #
                # if we have permission to write to teh file_src_dir then
                # try to do so. This means it's installed for all uses from this
                # install of ImageMetaTag:
                if os.access(file_src_dir, os.W_OK):
                    pako_to_dir = file_src_dir
                    # now get pako:
                    get_pako(pako_to_dir=pako_to_dir)
                    # and copy it to where it's needed for this call:
                    shutil.copy(js_src, js_dest)
                else:
                    # put pako js file into the target dir. At least it will
                    # be available for subsequent writes to that dir:
                    pako_to_dir = file_dir
                    # now get pako to that dir:
                    get_pako(pako_to_dir=pako_to_dir)
            else:
                # copy the file:
                shutil.copy(js_src, js_dest)
        # finally, make a note:
        js_files.append(js_to_copy)

    return js_files

def get_pako(pako_to_dir=None):
    '''
    Obtains the required pako javascript code from remote host, to a given
    javascript directory. If the javascript dir is not supplied, then
    the 'javascript' directory alongside the ImageMetaTag python code is used.
    '''
    import tarfile
    from urllib.request import urlopen

    # set up pako into the current imt_dir:
    if pako_to_dir is None:
        pako_to_dir = os.path.join(imt.__path__[0], 'javascript')

    # Open the url
    pako_urlopen = urlopen(PAKO_SOURCE_TAR)
    print("downloading " + PAKO_SOURCE_TAR)
    # Open our local file for writing
    with tempfile.NamedTemporaryFile('w', suffix='.tar.gz', prefix='pako_',
                                     delete=False) as local_file:
        local_file.write(pako_urlopen.read())
        targz_file = local_file.name
    pako_urlopen.close()
    # now extract the file we need:
    with tarfile.open(name=targz_file, mode='r:gz') as tgz:
        if not tarfile.is_tarfile:
            raise ValueError('Downloaded pako tar.gz file cannot be read.')
        else:
            target = 'pako-{}/dist/{}'.format(PAKO_RELEASE, PAKO_JS_FILE)
            target_file = tgz.extractfile(target)
            if target_file:
                with open(os.path.join(pako_to_dir, PAKO_JS_FILE), 'w') as final_file:
                    for line in target_file:
                        final_file.write(line)
    os.remove(targz_file)

def _indent_up_one(ind):
    'increases the indent level of an input ind by one'
    n_indents = int(len(ind) / LEN_INDENT)
    return INDENT * (n_indents + 1)

def _indent_down_one(ind):
    'decreases the indent level of an input ind by one'
    n_indents = int(len(ind) / LEN_INDENT)
    return INDENT * max(n_indents - 1, 0)

def _py_to_js_bool(py_bool):
    'Converts a python boolean to a string, in javascript bool format (all lower case)'
    if py_bool is True:
        return 'true'
    elif py_bool is False:
        return 'false'
    else:
        raise ValueError('input to _py_to_js_bool is not a boolean, it is: %s' % py_bool)
