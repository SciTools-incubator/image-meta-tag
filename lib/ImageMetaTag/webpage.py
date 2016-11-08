'''
This sub-module contains functions to write out an :class:`ImageMetaTag.ImageDict` to a webpage.

The webpages are made up of a single .html file, which is the page to be loaded to view the images.
Alongside this is a short ImageMetaTag javascript library held in a '.js' file 
(currently held in a single file) and a .json file contain the :class:`ImageMetaTag.ImageDict`
tree strcuture as a JSON data strcuture.

This can either be done using write_full_page, to produce a page with just a set of
selectors to browse the ImageDict, or the different components can be added to a
page as it is being constructed (reading in an html template, for instance).

To write out a full page, use :func:`ImageMetaTag.webpage.write_full_page`.

If the latter, then the following sections are needed:

    * :func:`ImageMetaTag.webpage.write_js_to_header` - writes out the javascript information to the\
                                                html header
    * :func:`ImageMetaTag.webpage.write_js_placeholders` - writes out the placeholders that\
                                                        the javascript will write images to.
    * :func:`ImageMetaTag.webpage.write_json` - writes out the :class:`ImageMetaTag.ImageDict`\
                                                as a json.dump to a json file
    * :func:`ImageMetaTag.webpage.copy_required_javascript` - copies required javascript library \
                                                          to the required location.
                                                          
.. TIP:: At present, the only webpage style that can be produced is a set of horizontal dropdown\
menus, but more will hopefully be added soon. 

.. moduleauthor:: Malcolm Brooks https://github.com/malcolmbrooks
'''

import os, json, pdb, shutil, tempfile, re
import ImageMetaTag as imt

# single indent to be used on the output webpage 
INDENT = '  '
LEN_INDENT = len(INDENT)

def write_full_page(img_dict, filepath, title, page_filename=None, tab_s_name=None,
                    preamble=None, postamble=None,
                    initial_selectors=None,show_selector_names=False,
                    url_type='int', only_show_rel_url=False, verbose=False,
                    style='horiz dropdowns', write_intmed_tmpfile=False,
                    description=None, keywords=None):
    '''
    Writes out an :class:`ImageMetaTag.ImageDict` as a webpage, to a given file location.
    The file is overwritten.

    If the img_dict supplied is None, rather than the appropriate class, then a page will
    be produced with the image selectors missing, and a message saying no images are available.

    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.

    * page_filename - the file name, within the directory (defaults to the name of the file) \
                      but can be set if tab_s_name is also used.
    * tab_s_name : used to denote the name of the page, when it is used as a frame \
                   of a larger page.
    * preamble : html text added at the top of the <body> text, but before the ImageMetaTag \
                 section. Can be quite extensive.
    * postable : html text added after the ImageMetaTag section.
    * initial_selectors - A list of initial values for the selectors, to be passed into \
                          :func:`ImageMetaTag.webpage.write_js_setup`.
    * show_selector_names - switches on diplsaying the selector full names defined by the \
                            :class:`ImageMetaTag.ImageDict`.full_name_mapping
    * url_type - determines the type of URL at the bottom of the ImageMetaTag section. Can be \
                 'int' or 'str'.
    * only_show_rel_url - If True, the wepage will only show relative urls in is link section.
    * verbose - If True, stdout will be more verbose
    * style - the style of output page to write, currently only 'horiz dropdowns' is valid
    * write_intmed_tmpfile - If True, files are written out to temporary filenames and then \
                             moved when completed.
    * description - html description metadata
    * keywords - html keyword metadata
    
    Returns a list of files that the the created webpage is dependent upon
    '''
    
    page_dependencies = []

    if not (isinstance(img_dict, imt.ImageDict) or img_dict is None):
        raise ValueError('write_full_page works on an ImageMetaTag ImageDict.')
    
    if page_filename is None:
        page_filename = os.path.basename(filepath)

    # other files involved:
    file_dir, file_name = os.path.split(filepath)
    page_dependencies.append(file_name)
    
    if img_dict is None:
        pass
    else:
        # we have real data to work with:
        dict_depth = img_dict.dict_depth(uniform_depth=True)
        
        file_name_no_ext = os.path.splitext(file_name)[0]
        # json file to hold the image_dict branching data etc:
        json_file = file_name_no_ext + '.json'
        page_dependencies.append(json_file)
        json_filepath = os.path.join(file_dir, json_file)
        if write_intmed_tmpfile:
            with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='imt_',
                                             dir=file_dir, delete=False) as json_file_obj:
                # now write out a json file:
                write_json(img_dict, json_file_obj)
                tmp_json_filepath = json_file_obj.name
        else:
            write_json(img_dict, json_filepath)
            
        # now make sure the required javascript library is copied over to the file_dir:
        js_file = copy_required_javascript(file_dir, style)
        page_dependencies.append(js_file)
        
        # this is the internal name the different selectors, associated lists for the selectors, and
        # the list of files (all with a numbered suffix):
        selector_prefix = 'sel'
        list_prefix = 'list'
        file_list_name = 'file_list'
        url_separator = '|'
        
    # now write the actual output file:
    if write_intmed_tmpfile:
        # get a temporary file:
        with tempfile.NamedTemporaryFile('w', suffix='.html', prefix='imt_',
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
        out_file.write(ind + '<html>\n')
        # increase the indent level:
        ind = _indent_up_one(ind)
        out_file.write(ind + '<head>\n')
        ind = _indent_up_one(ind)
        if not title is None:
            out_file.write('{}<title>{}</title>\n'.format(ind, title))
        out_file.write(ind+'<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">\n')
        
        if style == 'horiz dropdowns':
            # write out a little css at the top:
            out_file.write(ind + '<style>')
            out_file.write(ind + 'body, div, dl, dt, dd, li, h1, h2, h3, h4, h5, h6, pre, form,')
            out_file.write(ind + '            fieldset, input, textarea, p, blockquote, th, td {')
            out_file.write(ind + '    margin: 0;')
            out_file.write(ind + '    padding: 0;')
            out_file.write(ind + '}')
            out_file.write(ind + 'fieldset, img {')
            out_file.write(ind + '    border: 0 none;')
            out_file.write(ind + '}')
            out_file.write(ind + 'body { ')
            out_file.write(ind + '    font: 12px Myriad,Helvetica,Tahoma,Arial,clean,sans-serif;')
            out_file.write(ind + '    *font-size: 75%;')
            out_file.write(ind + '}')
            out_file.write(ind + 'h1 {')
            out_file.write(ind + '    font-size: 1.5em; ')
            out_file.write(ind + '    font-weight: normal;')
            out_file.write(ind + '    line-height: 1em; ')
            out_file.write(ind + '    margin-top: 1em;')
            out_file.write(ind + '    margin-bottom:0;')
            out_file.write(ind + '}')
            out_file.write(ind + 'h2 { ')
            out_file.write(ind + '    font-size: 1.1667em; ')
            out_file.write(ind + '    font-weight: bold; ')
            out_file.write(ind + '    line-height: 1.286em; ')
            out_file.write(ind + '    margin-top: 1.929em; ')
            out_file.write(ind + '    margin-bottom:0.643em;')
            out_file.write(ind + '}')
            out_file.write(ind + 'h3, h4, h5, h6 {')
            out_file.write(ind + '    font-size: 1em; ')
            out_file.write(ind + '    font-weight: bold; ')
            out_file.write(ind + '    line-height: 1.5em; ')
            out_file.write(ind + '    margin-top: 1.5em; ')
            out_file.write(ind + '    margin-bottom: 0;')
            out_file.write(ind + '}')
            out_file.write(ind + 'p { ')
            out_file.write(ind + '    font-size: 1em; ')
            out_file.write(ind + '    margin-top: 1.5em; ')
            out_file.write(ind + '    margin-bottom: 1.5em; ')
            out_file.write(ind + '    line-height: 1.5em;')
            out_file.write(ind + '}')
            out_file.write(ind + 'pre, code { ')
            out_file.write(ind + '    font-size:115%;')
            out_file.write(ind + '    *font-size:100%;')
            out_file.write(ind + '    font-family: Courier, "Courier New"; ')
            out_file.write(ind + '    background-color: #efefef; ')
            out_file.write(ind + '    border: 1px solid #ccc;')
            out_file.write(ind + '}')
            out_file.write(ind + 'pre { ')
            out_file.write(ind + '    border-width: 1px 0; ')
            out_file.write(ind + '    padding: 1.5em;')
            out_file.write(ind + '}')
            out_file.write(ind + 'table {  font-size:100%; }')
            out_file.write(ind + '</style>')
        
        
        if img_dict is None:
            # now write out the specific stuff to the html header:
            write_js_to_header(img_dict,
                               file_obj=out_file,
                               pagename=page_filename, tabname=tab_s_name,
                               ind=ind,
                               description=description, keywords=keywords)        
        else:
            # now write out the specific stuff to the html header:
            write_js_to_header(img_dict, initial_selectors=initial_selectors,
                               file_obj=out_file, json_file=json_file, js_file=js_file,
                               pagename=page_filename, tabname=tab_s_name,
                               selector_prefix=selector_prefix, url_separator='|', url_type=url_type,
                               only_show_rel_url=only_show_rel_url,
                               style=style, ind=ind,
                               description=description, keywords=keywords)        
        # now close the script and head:
        ind = _indent_down_one(ind)
        out_file.write(ind + '</script>\n')
        ind = _indent_down_one(ind)
        out_file.write(ind + '</head>\n')
            
        # now start the body:
        margins = 'leftmargin="0" topmargin="0" marginwidth="0" marginheight="0"'
        bgcolor = 'bcolor="#FFFFFF"'
        text_color =  'text="#000000"'
        out_file.write('{}<body {} {} {}>\n'.format(ind, bgcolor, text_color, margins))
    
        if not preamble is None:
            out_file.write(preamble)
    
    
        if img_dict is None:
            out_file.write('<p><h1>No images are available for this page.</h1></p>')
        else:
            # now write out the end, which includes the placeholders for the actual
            # stuff that appears on the page:
            if show_selector_names:
                level_names = img_dict.level_names
            else:
                level_names = False
            write_js_placeholders(file_obj=out_file, dict_depth=img_dict.dict_depth(),
                                  style=style, level_names=level_names)
    
        if not postamble is None:
            out_file.write(postamble + '\n')

        # finish the body, and html:
        out_file.write(ind + '</body>\n')
        out_file.write('\n</html>')
    
        if  write_intmed_tmpfile:
            # now move the json, then the html files:
            if img_dict is not None:
                os.chmod(tmp_json_filepath, 0644)
                shutil.move(tmp_json_filepath, json_filepath)
            os.chmod(tmp_html_filepath, 0644)
            shutil.move(tmp_html_filepath, filepath)
    
        if verbose:
            print 'File "%s" complete.' % filepath

    return page_dependencies

def write_js_to_header(img_dict, initial_selectors=None, style=None,
                       file_obj=None, json_file=None, js_file=None,
                       pagename=None, tabname=None, selector_prefix=None,
                       url_separator='|', url_type='str', only_show_rel_url=False,
                       ind=None,
                       description=None, keywords=None):
    '''
    Writes out the required ImageMetaTag config and data paths into a html header section
    for an input :class:`ImageMetaTag.ImageDict`.

    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.

    * initial_selectors - A list of initial values for the selectors.
    * style - the style of the output webpage, currently only 'horiz dropdowns' is available
    * file_obj - the open file object to write the header to.
    * json_file - the json (or other similar object) containing the representation of \
                  the ImageDict data.
    * js_file - the javascript file containing the actual scripting for the selected style.
    * pagename - the file name, within the directory (defaults to the name of the file) \
                 but can be set if tab_s_name is also used.
    * tabname : used to denote the name of the page, when it is used as a frame \
                of a larger page.
    * url_type - determines the type of URL at the bottom of the ImageMetaTag section. Can be \
                 'int' or 'str'.
    * only_show_rel_url - If True, the wepage will only show relative urls in is link section.
    * ind - indentation going into the header section.
    * description - html description metadata7
    * keywords - html keyword metadata
    '''
    
    if not (isinstance(img_dict, imt.ImageDict) or img_dict is None):
        raise ValueError('Input img_dict is not an ImageMetaTag ImageDict')

    if not description is None:
        file_obj.write('{}<meta name="description" content="{}">\n'.format(ind, description))
    if not keywords is None:
        file_obj.write('{}<meta name="keywords" content="{}">\n'.format(ind, keywords))

    if not img_dict is None:
        # add a reference to the data structure:
        file_obj.write('{}<script type="text/javascript" src="{}"></script>\n'.format(ind, json_file))
        # now add a reference to the javascript functions to implement the style:
        file_obj.write('{}<script type="text/javascript" src="{}"></script>\n'.format(ind, js_file))
        
        # now write out the javascript cnfiguration variables:
        file_obj.write(ind + '<script type="text/javascript">\n')
        ind = _indent_up_one(ind)
        
        # in case the page we are writing is embedded as a frame, write out the top
        # level page here;
        file_obj.write('{}var pagename = "{}"\n'.format(ind, pagename))
        # the tab name is used in setting up the URL in nested frames:
        file_obj.write('{}var tab_name = "{}";\n'.format(ind, tabname))
    
        dict_depth = img_dict.dict_depth()
        # the key_to_selector variable is what maps each set of keys onto a selector on the page:
        key_to_selector = str([selector_prefix + str(x) for x in range(dict_depth)])
        file_obj.write('{}var key_to_selector = {};\n'.format(ind, key_to_selector))
    
        # and the width is what determines how large the selector appears on the page:
        file_obj.write('{}var selector_widths = {};\n'.format(ind, str(img_dict.selector_widths)))
        
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
        # (it will be overwritten later if the URL changes it, and when selectors/stepping change it):
        if initial_selectors is None:
            # if it's not set, then set it to something invalid, and the validator
            # in the javascript will sort it out. It MUST be the right length though:
            file_obj.write('{}var selected_id = {}\n;'.format(ind, str([-1]*dict_depth)))
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
            file_obj.write('{}var selected_id = {};\n'.format(ind, initial_selectors_as_inds))
        
        # now write out the lists of keys, to the different levels:
        keys_to_js = [str(x[1]) for x in img_dict.keys.iteritems()]
        file_obj.write('{}var key_lists = [{},\n'.format(ind, keys_to_js[0]))
        ind = _indent_up_one(ind)
        for i_depth in range(1, dict_depth):
            file_obj.write('{}{},\n'.format(ind, keys_to_js[i_depth]))
        ind = _indent_down_one(ind)
        file_obj.write(ind + '];\n')
        
        # now some top level things:
        if style == 'horiz dropdowns':
            file_obj.write('''
    {0}// other top level derived variables
    {0}// the depth of the ImageMetaTag ImageDict (number of selectors):
    {0}var n_deep = selected_id.length;
    {0}// a list of the options available to the animator buttons, with the current selectio
    {0}var anim_options = [];
    {0}// the index of the current option for the animator:
    {0}var anim_ind = 0;
    '''.format(ind))
        
        # now, the main call:
        file_obj.write(ind + 'window.onload = function() {\n')
        ind = _indent_up_one(ind)
        file_obj.write(ind + '// redefine onload, so it does this:\n')
        file_obj.write(ind + 'imt_main();\n')
        ind = _indent_down_one(ind)
        file_obj.write(ind + '};\n')
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

def write_json(img_dict, json_file):
    '''
    Writes a json dump of the :class:`ImageMetaTag.ImageDict` tree strucuture to a target file path
    '''
    if not isinstance(img_dict, imt.ImageDict):
        raise ValueError('input img_dict is not an ImageMetaTag.ImageDict')
    # TODO: ivestigate using zblib to compress this, and pako.js to decompress, client side:
    dict_as_json = json.dumps(img_dict.dict, separators=(',',':'))

    # if we're not doing any fancy compression, then use subdirectories to reduce the string size:
    for i_sd, subdir in enumerate(img_dict.subdirs):
        dict_as_json = re.sub('"{}'.format(subdir), 'sd[{}]+"'.format(i_sd), dict_as_json)

    out_str = '''
var sd = {};
var imt = {};
'''.format(img_dict.subdirs, dict_as_json)
    
    if isinstance(json_file, str):
        # input is a string, assume it's the file path to write to:
        with open(json_file, 'w') as file_obj:
            file_obj.write(out_str)
    else:
        # input is a file object:
        json_file.write(out_str)

def write_js_placeholders(file_obj=None, dict_depth=None, selector_prefix=None,
                          style='horiz dropdowns', level_names=False):
    '''
    Writes the placeholders into the page body, for the javascript to manipulate

    * file_obj - an open file object to write to
    * dict_dept - the depth of the :class:`ImageMetaTag.ImageDict` being written
    * selector_prefix - prefix for the variable names of the selectors (these are visible to \
                        those people viewing the webpage!)
    * style - In future, it would be great to write out different types of webpages. For now \
              they are always horizontal dropdown menus: 'horiz dropdowns'.
    * level_names - if supplied, this need to be a list of full names, for the selectors, of \
                    length dict_depth.
    '''

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
        # for each level of depth in the plot dictionary, add a span to hold the selector:
        if apply_level_names:
            # if we want labelled selectors, then write out
            # a table, with pairs of label, selector, in columns:
            file_obj.write('''
   <table border=0 cellspacing=0 cellpadding=0 style='border-spacing: 3px 0;'>
     <tr>
''')
            for level in range(dict_depth):
                file_obj.write('       <td>{}&nbsp;&nbsp;</td>\n'.format(level_names[level]))
            file_obj.write('''     </tr>
     <tr>
''')
            for level in range(dict_depth):
                file_obj.write('       <td><span id="%s%s">&nbsp;</span></td>\n' % (selector_prefix, level))
            file_obj.write('''     </tr>
''')
            # add the placeholder for animators buttons:
            file_obj.write('''     <tr>
      <td colspan={}>
        <span id="animator1">&nbsp;</span>
        <span id="animator2">&nbsp;</span>
      </td>
    </tr>
   </table>
'''.format(dict_depth))
        else:
            # simply a set of spans, in a line:
            for lev in range(dict_depth):
                file_obj.write('''
   <span id="%s%s">&nbsp;</span>''' % (selector_prefix, lev))
            file_obj.write('\n   <br>')
            # add the placeholder for animators buttons:
            file_obj.write('''
   <span id="animator1">&nbsp;</span>
   <span id="animator2">&nbsp;</span>
       <br>
    ''')
            
        # now add somewhere for the image to go:
        file_obj.write('''   <div id="the_image">Please wait while the page is loading</div>
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

def _indent_up_one(ind):
    'increases the indent level of an input ind by one'
    n_indents = len(ind) / LEN_INDENT
    return INDENT * (n_indents + 1) 
    
def _indent_down_one(ind):
    'decreases the indent level of an input ind by one'
    n_indents = len(ind) / LEN_INDENT
    return INDENT * max(n_indents - 1, 0) 
    
def _py_to_js_bool(py_bool):
    'Converts a python boolean to a string, in javascript bool format (all lower case)'
    if py_bool is True:
        return 'true'
    elif py_bool is False:
        return 'false'
    else:
        raise ValueError('input to _py_to_js_bool is not a boolean, it is: %s' % py_bool)
