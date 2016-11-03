'''
Sub-module containing functions to write out an ImageDict to a webpage.

This can either be done using write_full_page, to produce a page with just a set of
selectors to browse the ImageDict, or the different components can be added to a
page as it is being constructed (reading in an html template, for instance).

To write out a full page, use :func:`ImageMetaTag.webpage.write_full_page`.

If the latter, then the following sections are needed:

    * :func:`ImageMetaTag.webpage.write_js_placeholders` - writes out the placeholders that \
                                                        the javascript will write images to.
    * :func:`ImageMetaTag.webpage.write_json` - writes out the :class:`ImageMetaTag.ImageDict` \
                                                as a json.dump to a json file
    

.. warning::
   The Javascript code written by these routines works well up to ~250,000 to 500,000 images,
   depending on the ImageDict branching. Pages larger than this can be quite slow, and the
   Javascript needs refactoring to cope with this.


.. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks
'''

import os, json, pdb, shutil
import ImageMetaTag as imt

def write_full_page(img_dict, filepath, title, page_filename=None, tab_s_name=None,
                    preamble=None, postamble=None, internal=False,
                    initial_selectors=None,
                    url_type='int', only_show_rel_url=False, verbose=False,
                    style='horiz dropdowns',
                    description=None, keywords=None):
    '''
    Writes out an ImageDict as a webpage, to a given file location.
    The file is overwritten.

    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.

    * page_filename - the file name, within the directory (defaults to the name of the file) \
                      but can be set if tab_s_name is also used.
    * tab_s_name : used to denote the name of the page, when it is used as a frame \
                   of a larger page.
    * preamble : html text added at the top of the <body> text, but before the ImageMetaTag \
                 section. Can be quite extensive.
    * postable : html text added after the ImageMetaTag section.
    * internal - If True, internal copies of the dojo Javascript API and css files will be used.
    * initial_selectors - A list of initial values for the selectors.
    * url_type - determines the type of URL at the bottom of the ImageMetaTag section. Can be \
                 'int' or 'str'.
    * only_show_rel_url - If True, the wepage will only show relative urls in is link section.
    * verbose - If True, stdout will be more verbose
    * description - html description metadata
    * keywords - html keyword metadata
    '''

    if not isinstance(img_dict, imt.ImageDict):
        raise ValueError('write_full_page work on an ImageMetaTag ImageDict.')
    dict_depth = img_dict.dict_depth(uniform_depth=True)
    
    if page_filename is None:
        page_filename = os.path.basename(filepath)

    # other files involved:
    file_dir, file_name = os.path.split(filepath)
    file_name_no_ext = os.path.splitext(file_name)[0]
    # json file to hold the image_dict branching data etc:
    json_file = file_name_no_ext + '.json'
    json_filepath = os.path.join(file_dir, json_file)
    json_filepath_tmp = json_filepath + '.tmp'

    # now write out a json file:
    write_json(img_dict, json_filepath_tmp)
    shutil.move(json_filepath_tmp, json_filepath)
    
    # now make sure the required javascript library is copied over to the file_dir:
    js_file = copy_required_javascript(file_dir, style)
    
    # this is the internal name the different selectors, associated lists for the selectors, and
    # the list of files (all with a numbered suffix):
    selector_prefix = 'sel'
    list_prefix = 'list'
    file_list_name = 'file_list'
    url_separator = '|'

    indent = '  '
    # open the file - this is a nice and simple file so just use the with open...
    with open(filepath, 'w') as out_file:
        # current indent, is 1 indent:
        ind = indent * 1
        # write out the start of the file:
        out_file.write('<html>\n')
        out_file.write('{}<head>\n'.format(ind))
        # now moving up an indent level:
        ind = indent * 2
        if not title is None:
            out_file.write('{}<title>{}</title>\n'.format(ind, title))
        out_file.write(ind+'<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">\n')
        if not description is None:
            out_file.write('{}<meta name="description" content="{}">\n'.format(ind, description))
        if not keywords is None:
            out_file.write('{}<meta name="keywords" content="{}">\n'.format(ind, keywords))
        
        # TODO: make an indent controlling function
        
        # TODO: have the imt head section as a function...
        
        # add a reference to the data structure:
        out_file.write('{}<script type="text/javascript" src="{}"></script>\n'.format(ind, json_file))
        # now add a reference to the javascript functions to implement the style:
        out_file.write('{}<script type="text/javascript" src="{}"></script>\n'.format(ind, js_file))
        
        # now write out the javascript cnfiguration variables:
        out_file.write(ind + '<script type="text/javascript">\n')
        ind = indent * 3
        
        # in case the page we are writing is embedded as a frame, write out the top
        # level page here;
        out_file.write('{}var pagename = "{}"\n'.format(ind, page_filename))
        # the tab name is used in setting up the URL in nested frames:
        out_file.write('{}var tab_name = "{}";\n'.format(ind, tab_s_name))

        # the key_to_selector variable is what maps each set of keys onto a selector on the page:
        key_to_selector = str([selector_prefix + str(x) for x in range(dict_depth)])
        out_file.write('{}var key_to_selector = {};\n'.format(ind, key_to_selector))
    
        # and the width is what determines how large the selector appears on the page:
        out_file.write('{}var selector_widths = {};\n'.format(ind, str(img_dict.selector_widths)))
        
        # this determines whether a selector uses the animation controls on a page:
        out_file.write('{}var anim_sel = {};\n'.format(ind, img_dict.selector_animated))
        # and the direction the animation runs in:
        out_file.write('{}var anim_dir = {};\n'.format(ind, img_dict.animation_direction))
        # and the direction the animation runs in:
    
        # the url_separator is the text character that goes between the variables in the url:
        if url_separator == '&':
            msg = 'Cannot use "&" as the url_separator, as some strings will '
            msg += 'become html special characters. For instance &para-global '
            msg += 'will be treated as a paragraph then -global, not the intended string.'
            raise ValueError(msg)
        out_file.write('{}var url_separator = "{}";\n'.format(ind, url_separator))

        # the url_type determines whether the url is full of integers (int), with meaningful
        # values internally or text which looks more meaningful to the user:
        out_file.write('{}var url_type = "{}";\n'.format(ind, url_type))
        # the show_rel_url logical (converted to a string to init a javascript bool)
        out_file.write('{}var show_rel_url = {};\n'.format(ind, py_to_js_bool(only_show_rel_url)))
        
        # the selected_id needs to be defined here too, as it's used as a global variable
        # (it will be overwritten later if the URL changes it, and when selectors/stepping change it):
        if initial_selectors is None:
            # if it's not set, then set it to something invalid, and the validator
            # in the javascript will sort it out. It MUST be the right length though:
            out_file.write('{}var selected_id = {}\n;'.format(ind, str([-1]*dict_depth)))
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
                        raise ValueError('initial_selectors contains indices which are out of range')
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
            out_file.write('{}var selected_id = {};\n'.format(ind, initial_selectors_as_inds))
        
        # now write out the lists of keys, to the different levels:
        keys_to_js = [str(x[1]) for x in img_dict.keys.iteritems()]
        out_file.write('{}var key_lists = [{},\n'.format(ind, keys_to_js[0]))
        ind = indent * 4
        for i_depth in range(1, dict_depth):
            out_file.write('{}{},\n'.format(ind, keys_to_js[i_depth]))
        ind = indent * 3
        out_file.write(ind + '];\n')
        
        # now some top level things:
        if style == 'horiz dropdowns':
            out_file.write('''
{0}// other top level derived variables
{0}// the depth of the ImageMetaTag ImageDict (number of selectors):
{0}var n_deep = selected_id.length;
{0}// a list of the options available to the animator buttons, with the current selectio
{0}var anim_options = [];
{0}// the index of the current option for the animator:
{0}var anim_ind = 0;
'''.format(ind))
        
        # now, the main call:
        out_file.write(ind + 'window.onload = function() {\n')
        ind = indent * 4
        out_file.write(ind + '// redefine onload, so it does this:\n')
        out_file.write(ind + 'imt_main();\n')
        ind = indent * 3
        out_file.write(ind + '};\n')
        # END of the imt specifc header content:
        
        
        # now close the script and head:
        ind = indent * 2
        out_file.write(ind + '</script>\n')
        ind = indent * 1
        out_file.write(ind + '</head>\n')
        
        # now start the body:
        margins = 'leftmargin="0" topmargin="0" marginwidth="0" marginheight="0"'
        bgcolor = 'bcolor="#FFFFFF"'
        text_color =  'text="#000000"'
        out_file.write('{}<body {} {} {}>\n'.format(ind, bgcolor, text_color, margins))

        if not preamble is None:
            out_file.write(preamble)

        # now write out the end, which includes the placeholders for the actual stuff that appears on the page:
        write_js_placeholders(file_obj=out_file, dict_depth=img_dict.dict_depth(),
                              style=style)

        if not postamble is None:
            out_file.write(postamble)

        # finish the body, and html:
        out_file.write(ind + '</body>')
        out_file.write('</html>')

    if verbose:
        print 'File "%s" complete.' % filepath


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

def write_json(img_dict, json_file_path):
    '''
    Writes a json dump to a target file path
    '''
    if not isinstance(img_dict, imt.ImageDict):
        raise ValueError('input img_dict is not an ImageMetaTag.ImageDict')
    with open(json_file_path, 'w') as file_obj:
        file_obj.write('var sd = %s;\n' % img_dict.subdirs)
        
        dict_as_json = json.dumps(img_dict.dict, separators=(',',':'))
        # TODO: compress this, with reg expressions to replace the strings with placeholders for
        # key names, subdirectories, and lots of other things....
        ## Or, use messagepack
        file_obj.write('var imt = %s;\n\n' % dict_as_json)

def write_js_placeholders(file_obj=None, dict_depth=None, selector_prefix=None,
                          style='horiz dropdowns'):
    '''
    Writes the placeholders into the page body, for the javascript to manipulate

    * file_obj - an open file object to write to
    * dict_dept - the depth of the :class:`ImageMetaTag.ImageDict` being written
    * selector_prefix - prefix for the variable names of the selectors (these are visible to \
                        those people viewing the webpage!)
    * style - In future, it would be great to write out different types of webpages. For now \
              they are always horizontal dropdown menus: 'horiz dropdowns'.
    '''

    if selector_prefix is None:
        selector_prefix, _junk1, _junk2 = write_js_setup_defaults()

    if style == 'horiz dropdowns':
        file_obj.write('''
<!-- Now f"or some placeholders for the scripts to put content -->
<table border=0 cellspacing=0 cellpadding=0 width=99% align=center>
 <tr>
  <td>
   <font size=3>
   <br>''')

        # for each level of depth in the plot dictionary, add a span to hold the selector:
        # TODO: include the selector full_name_mapping
        for lev in range(dict_depth):
            file_obj.write('''
   <span id="%s%s">&nbsp;</span>''' % (selector_prefix, lev))

        # now add somewhere for the image to go:
        file_obj.write('''
   <br>
   <span id="animator1">&nbsp;</span>
   <span id="animator2">&nbsp;</span>
   <br>
   <div id="the_image">Please wait while the page is loading</div>
   <br>
   <div id="the_url">....</div>''')

        file_obj.write('''
   </font>
  </td>
 </tr>
</table>

''')

    else:
        raise ValueError('"%s" tyle of content placeholder not defined' % style)

def copy_required_javascript(file_dir, style, overwrite=True):
    '''
    Copies the required javascript library to the directory
    containing the required page (file_dir) for a given webpage style.
    
    If a file is already present it will be checked based it's first line.
    If the file is different, it will be overwritten if overwrite is True.
    '''

    if style == 'horiz dropdowns':
        file_to_copy = 'imt_dropdown.js'
        # get this from the installed ImageMetaTag directory:
        file_src_dir = imt.__path__[0].replace('lib/ImageMetaTag', 'javascript')
        first_line = '// ImageMetaTag dropdown menu scripting - vn0.2\n'
    else:
        raise ValueError('Javascript library not set up for style: {}'.format(style))

    if not os.path.isfile(os.path.join(file_dir, file_to_copy)):
        # file isn't in target dir, so copy it:
        shutil.copy(os.path.join(file_src_dir, file_to_copy),
                    os.path.join(file_dir, file_to_copy))
    else:
        # the file is there, check it's right:
        with open(os.path.join(file_dir, file_to_copy)) as file_obj:
            this_first_line = file_obj.readline()
        if first_line == this_first_line:
            # the file is good, move on:
            pass
        else:
            if overwrite:
                shutil.copy(os.path.join(file_src_dir, file_to_copy),
                            os.path.join(file_dir, file_to_copy))
            else:
                print '''File: {}/{} differs to the expected contents, but is 
not being overwritten. Your webpage may be broken!'''.format(file_dir, file_to_copy)
        
    return file_to_copy

def py_to_js_bool(py_bool):
    'Converts a python boolean to a string, in javascript bool format (all lower case)'
    if py_bool is True:
        return 'true'
    elif py_bool is False:
        return 'false'
    else:
        raise ValueError('input to py_to_js_bool is not a boolean, it is: %s' % py_bool)
