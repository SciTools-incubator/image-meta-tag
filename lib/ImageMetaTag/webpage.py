'''
Sub-module containing fucntions to write out an ImageDict to a webpage.

This can either be done using write_full_page, to produce a page with just a set of 
selectors to browse the ImageDict, or the different components can be added to a 
page as it is being constructed (reading in an html template, for instance).

If the latter, then the following sections are needed:
   
   write_js_setup - writes out the scripting required on a page
   write_js - writes out the contents of the ImageDict as a javascript array
   write_js_placeholders - writes out the placeholders that thje javascript will write images to.

TODO: set up the dojo scripts/resources in a section for template type files

@author: Malcolm.E.Brooks@metoffice.gov.uk
'''

import os
from ImageMetaTag import ImageDict


def write_full_page(img_dict, filepath, page_longname, preamble=None, postamble=None, verbose=False, internal=False):
    '''
    Writes out an ImageDict as a webpage, to a given filepath.
    The file is overwritten.
    
    Currently only able to write out a page with horizontal dropdown menus, but other
    webpage styles could be added.
    
    Options:
        verbose: If True, stdout will be moer verbose
        internal: If True, internal copies of the dojo Javascript API and css files will be used.
    '''
    
    if not isinstance(img_dict, ImageDict):
        raise ValueError('write_full_page work on an ImageMetaTag ImageDict.')
    
    page_filename = os.path.basename(filepath)

    # this is the internal name the different selectors, associated lists for the selectors, and the
    # list of files (all with a numbered suffix):
    selector_prefix = 'sel'
    list_prefix = 'list'
    file_list_name = 'file_list'
    
    # open the file - this is a nice and simple file so just use the with open...
    with open(filepath, 'w') as out_file:
        # write out the start of the file:
        write_page_head_and_start_body(file_obj=out_file, title=page_longname, preamble=preamble, 
                                       description=None, keywords=None, internal=internal)
#       # write out the plot dictionary as a set of javascript variables, to be read into the scripts below: 
        write_js(img_dict, file_obj=out_file, selector_prefix=selector_prefix, list_prefix=list_prefix, \
                 file_list_name=file_list_name)
#        # write out the scripts/setup:
        write_js_setup(img_dict, file_obj=out_file, tab_s_name=None, \
                       selector_prefix=selector_prefix, list_prefix=list_prefix, file_list_name=file_list_name, 
                       pagename=page_filename, 
                       url_separator='|', url_type='int')
#        # now write out the end, which includes the placeholders for the actual stuff that appears on the page:
        write_js_placeholders(file_obj=out_file, dict_depth=img_dict.dict_depth(), style='horiz dropdowns')           
    
        if not postamble is None:
            out_file.write(postamble)
    
    if verbose:
        print 'File "%s" complete.' % filepath        
    
    
def write_page_head_and_start_body(file_obj=None, title=None, description=None, keywords=None, internal=False,
                                   preamble=None):
    'writes out header information for a html page, including the locations of dojo scripts and resources'
    
    # locations of the dojo javascript framework resources and api:
    dojo_local_css = ["http://www-nwp/~frtr/dojo-release-1.9.1/dojo/resources/dojo.css",
                      "http://www-nwp/~frtr/dojo-release-1.9.1/dijit/themes/soria/soria.css"]
    dojo_remote_css = ["http://ajax.googleapis.com/ajax/libs/dojo/1.9.1/dojo/resources/dojo.css", 
                       "http://ajax.googleapis.com/ajax/libs/dojo/1.9.1/dijit/themes/soria/soria.css"]
    dojo_local_script = "http://www-nwp/~frtr/dojo-release-1.9.1/dojo/dojo.js"
    dojo_remote_script = 'http://ajax.googleapis.com/ajax/libs/dojo/1.9.1/dojo/dojo.js'
    
    # start the page, with a appropriate headers/css resources:
    file_obj.write('''<html>
    <head>
    ''')
    if not title is None:
        file_obj.write('<title>%s</title>\n' % title)
    
    file_obj.write('<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">\n')
    if not description is None:
        file_obj.write('<meta name="description" content="%s">\n' % description)
    if not keywords is None:
        file_obj.write('<meta name="keywords" content="%s">\n' % keywords)
    
    if internal:
        dojo_css = dojo_local_css
    else:
        dojo_css = dojo_remote_css
        
    for css in dojo_css:
        file_obj.write('<link rel="stylesheet" href="%s" media="screen" />\n' % css)
    file_obj.write('</head>')
    
    # now start the body:
    file_obj.write('''
    <body class="soria" bgcolor="#FFFFFF" text="#000000" leftmargin="0" topmargin="0" marginwidth="0" marginheight="0">
    ''')
    
    if not preamble is None:
        file_obj.write(preamble)
    
    # and, crucially, declare the location of the javascript api:
    dojo_script_str = '''
<!-- access the dojo javascript library -->
<script type="text/javascript" src="'''
    if internal:
        dojo_script_str += dojo_local_script
    else:
        dojo_script_str += dojo_remote_script
    dojo_script_str += '" djConfig="isDebug:true, parseOnLoad:true"></script>\n\n'
    
    file_obj.write(dojo_script_str)
    
    
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

def write_js(img_dict, file_obj=None, selector_prefix=None, list_prefix=None, file_list_name=None, devmode=False):
    '''writes an ImageDict to a file object, as a set of javascript variables. The keys within 
    the plot dictionary are listed, with name specified by the list_prefix, and the file list (with the name
    from file_list_name) gives the files, and their indices, for all elements of the plot dictonary.
    '''
    
    if not isinstance(img_dict, ImageDict):
        raise ValueError('write_js works on an ImageMetaTag ImageDict.')

    #if not isinstance(file_obj, file):
    #    print type(file_obj)
    #    raise ValueError('The file_obj passed into PlotDictionary.write_js must be an open file object.')
     
    # this is the internal name the different selectors, associated lists for the selectors, and the
    # list of files (all with a numbered suffix):
    if selector_prefix is None:
        selector_prefix, junk1, junk2 = write_js_setup_defaults()
    if list_prefix is None:
        junk1, list_prefix, junk2 = write_js_setup_defaults()
    if file_list_name is None:
        junk1, junk2, file_list_name = write_js_setup_defaults()
    
    # the number of selectors/lists depends on the depth of the dictionary:
    dict_depth = img_dict.dict_depth(uniform_depth=True)
    
    # and the keys at each level of the dictionary, and the index (of the keys) of each
    # element at the bottom level of the dict:
    (keys, key_ind) = img_dict.dict_index_array(devmode=devmode)

    # and need to know how many there are at each level:
    n_keys_per_level = []
    for level in range(dict_depth):
        n_keys_per_level.append(len(keys[level]))
    
    
    # initialise the javascript section:
    try:
        file_obj.write('''<!--Plot dictionary listing:-->
<script type="text/javascript">
''')
    except:
        raise IOError, 'Cannot write to given file object'
    
    # start the plot dictionary var:
    file_obj.write('var key_lists = [\n')
    for level in range(dict_depth):
        for (key_id, key_name) in enumerate(keys[level]):
            if len(keys[level]) == 1:
                # this key list only has one thing in it!
                if level < dict_depth - 1:
                    # and it's not the last key;
                    file_obj.write('  {id: %s, list: [{id: 0, label: "%s"}]},\n' % (level, key_name))
                else:
                    # it's also the last key (so not comma!)
                    file_obj.write('  {id: %s, list: [{id: 0, label: "%s"}]}\n' % (level, key_name))
            elif key_id == 0:
                # the start of a key list:
                file_obj.write('  {id: %s, list: [{id: 0, label: "%s"},\n' % (level, key_name))
            elif key_id < len(keys[level]) - 1:
                # not the last item for this key list:
                file_obj.write('        {id: %s, label: "%s"},\n' %(key_id, key_name) )
            elif level < dict_depth - 1:
                # the last item for this key list, but it's not the last one:
                file_obj.write('        {id: %s, label: "%s"}]},\n' %(key_id, key_name) )
            else:
                # the last item of the last key list (so no comma!)
                file_obj.write('        {id: %s, label: "%s"}]}\n' %(key_id, key_name) )
                
    # and close the plot dictionary var:
    file_obj.write('];\n')

    ## test accessing these: 
    #file_obj.write('\nalert(key_lists[0].list[54].label)')
    #file_obj.write('\nalert(key_lists[1].list[2].label)')
    #file_obj.write('\nalert(key_lists[2].list[1].label)')
    
    # now write out all of the elements at the bottom level of the plot dictionary, and report 
    # their final details, and the id values of the key lists that refer to them: 

            
    # write out the file names:
    file_obj.write('var file_list = [\n')            
    for (item, ind_of_item) in enumerate(key_ind):
        tmp_dict = img_dict.dict
        for level in range(len(keys)):
            tmp_dict = tmp_dict[ keys[level][ ind_of_item[level] ] ]
        
        # at the bottom level, the result must not be a dict:
        if isinstance(tmp_dict, dict):
            raise ValueError, 'Bottom level of plot dictionary contains more dictionaries!'
        elif isinstance(tmp_dict, str):
            # a string - this content is the plot it's referring to:
            if item < len(key_ind)-1:
                file_obj.write('  "%s",\n' % (tmp_dict) )
            else:
                file_obj.write('  "%s"\n' % (tmp_dict) )
        elif isinstance(tmp_dict, list):
            # a list of plots:
            raise NotImplementedError, 'Not yet implemented defining a list of plots, but it could be done!'
        else:
            raise ValueError, 'Wrong type of thing at bottom of the plot dictionary.... \n  %s' % tmp_dict
    file_obj.write(']\n')

    # now the indices/ids:
    file_obj.write('var file_ids = [\n')            
    for (item, ind_of_item) in enumerate(key_ind):
        tmp_dict = img_dict.dict
        for level in range(len(keys)):
            tmp_dict = tmp_dict[ keys[level][ ind_of_item[level] ] ]
        
        # at the bottom level, the result must not be a dict:
        if isinstance(tmp_dict, dict):
            raise ValueError, 'Bottom level of plot dictionary contains more dictionaries!'
        elif isinstance(tmp_dict, (str, list)):
            # a string, or list of strings - this content is the plot it's referring to:
            if item < len(key_ind)-1:
                file_obj.write('  %s,\n' % (ind_of_item) )
            else:
                file_obj.write('  %s\n' % (ind_of_item) )
        else:
            raise ValueError, 'Wrong type of thing at bottom of the plot dictionary.... \n  %s' % tmp_dict
    file_obj.write(']\n')
    
    # close the javascript section:
    file_obj.write('''
</script>

''')

def write_js_setup(img_dict, file_obj=None, tab_s_name=None, 
                   selector_prefix=None, list_prefix=None, file_list_name=None, pagename=None, 
                   url_separator='|', url_type='int'):
    '''
    writes out the scripting reqruied to use an ImageDict to a file object
    The tab_s_name is used to denote the name of the page, when it is used as a frame of a larger page.
    '''

    # TODO: the actual Javascript is contained in strings in the function below. That's not very nice.

    if url_separator == '&':
        msg = 'Cannot use "&" as the url_separator, as some strings will become html special characters.'
        msg += ' For instance &para-global will be treated as a paragraph then -global, not the intended string.'
        raise ValueError(msg)
        
    #if not isinstance(file_obj, file):
    #    print type(file_obj)
    #    raise ValueError('The file_obj passed into PlotDictionary.write_js_setup must be an open file object.')
    
    if pagename is None:
        pagename = 'page.html'

    # this is the internal name the different selectors, associated lists for the selectors, and the
    # list of files (all with a numbered suffix):
    if selector_prefix is None:
        selector_prefix, junk1, junk2 = write_js_setup_defaults()
    if list_prefix is None:
        junk1, list_prefix, junk2 = write_js_setup_defaults()
    if file_list_name is None:
        junk1, junk2, file_list_name = write_js_setup_defaults()

    # get the depth of the plot dictionary (and demand it is of uniform depth):
    dict_depth = img_dict.dict_depth(uniform_depth=True)
    file_obj.write('''
<!-- now define the functions that do things on the page: -->
<script type="text/javascript">
''')
        
    file_obj.write('\nvar pagename = "%s"' % pagename)
    
    # the key_to_selector variable is what maps each set of keys onto a selector on the page:
    file_obj.write('\n\nvar key_to_selector = [')
    for lev in range(dict_depth):

        if lev == dict_depth-1:
            var_separator = ''
        else:
            var_separator = ','

        file_obj.write('''"%s%s"%s''' % (selector_prefix, lev, var_separator))
    file_obj.write('];')
    
    # and the width is what determines how large the selector appears on the page:
    file_obj.write('\nvar selector_widths = [')
    for lev in range(dict_depth):
        if lev == dict_depth-1:
            var_separator = ''
        else:
            var_separator = ','
        file_obj.write('''"%s"%s''' % (img_dict.selector_widths[lev], var_separator))
    file_obj.write('];')
    
    # this determines whether a selector uses the animation controls on a page:
    file_obj.write('\nvar anim_sel = %s;' % img_dict.selector_animated)
    # and the direction the animation runs in:
    file_obj.write('\nvar anim_dir = %s;' % img_dict.animation_direction)
    # and the direction the animation runs in:
    
    # the url_separator is the text character that goes between the variables in the url:
    file_obj.write('\nvar url_separator = "%s";' % url_separator)
    # the url_type determines whether the url is full of integers (int), with meaningful values internally
    # or text which looks more meaningful to the user:
    file_obj.write('\nvar url_type = "%s";'  % url_type)
    
    
    # the tab name is used in setting up the URL in nested frames:
    file_obj.write('\nvar tab_name = "%s";\n' % tab_s_name)
    
    # the selected_id needs to be defined here too, as it's used as a global variable
    # (it will be overwritten later if the URL changes it, and when selectors/stepping change it):
    file_obj.write('''
// start off with this initial selected id (and define it at this level, so it's always available):
// (slice, so it's a copy, not a reference!)
var selected_id = file_ids[0].slice();

// and this stores if a selector is valid for the selected_id
//var valid_selector = new Array(file_ids.length).fill( new Array(file_ids[0].length).fill(true) );
// IE 8 doesn't have fill!
var valid_selector = new Array(file_ids.length);//.fill( new Array(file_ids[0].length).fill(true) );
for (var i_file=0, l_files=file_list.length; i_file < l_files; i_file++){
  valid_selector[i_file] = new Array(file_ids[0].length);
  for (i_id=0, l_ids=file_ids[0].length; i_id < l_ids; i_id++){
    valid_selector[i_file][i_id] = true;
  };  
};
''')
    
    # now write out the javascript functions that actuall build the page:
    file_obj.write(r'''
// we need to compare the contents of arrays, so add a compare method to the Array's prototype:
Array.prototype.compares = function (array) {
  // written, using the example here http://stackoverflow.com/questions/7837456/comparing-two-arrays-in-javascript
  // as an aid to understanding...

  // if the comparator is not an array, then false:
  if (! array instanceof Array){
    return false;
  }  
  // if the input array is false, then return false:
  if (!array) {
    return false;
  }
  // compare the lengths - if not equal length, then false:
  if (this.length != array.length){
    return false;
  }

  // now loop through the elements of the list:
  // (optimisation: taking the length only once, to save doing it on each time through the loop)
  for (var ind = 0, len=this.length; ind < len; ind++){
    // check both elements are arrays:
    if ( this[ind] instanceof Array && array[ind] instanceof Array ){
      // recursively check the nested array:
      if (!this[ind].compares(array[ind]) ){
        return false;
      }
    } else if (this[ind] != array[ind]) {
      // this will also catch objects, which look equal, but won't compare: {x:y} != {x:y}
      return false;
    }
  }
  // if we've got to here, then the arrays compare!
  return true;
}
// and add the indexOf if it's not included:
if (!Array.prototype.indexOf) {
  Array.prototype.indexOf = function(obj, start) {
    for (var i = (start || 0), j = this.length; i < j; i++) {
      if (this[i] === obj) { return i; }
    }
    return -1;
  }
}

//////////////////////////////////////////////////////////////////////
// the following scripts are run, when everything is read in (domReady!)
require(["dojo/parser", 
  "dojo/_base/array", 
  "dijit/form/Select", 
  "dojo/data/ObjectStore", "dojo/store/Memory", "dojo/domReady!"], 

  //////////////////////////////////////////////////////////////////////
  // this is the script that is run, when domReady!:
  function (parser, array, Select, ObjectStore, Memory){
    // get the initial selected id, from default, or input on the URL
    get_selected_id();
    // display the URL to this page:
    write_url_to_div()
    // display the image that relates to the initial selected_id:
    set_img_from_id()
    // now write out the different selectors, from number/level 0:
    write_selectors(0)
    
  //////////////////////////////////////////////////////////////////////
  // Subroutines used in the script:
  //
  //////////////////////////////////////////////////////////////////////
  // get the initial id to present, from the input URL::
  function get_selected_id() {
    // initial selected id is the first one in the file_list (make a copy, don't point to it
    // or you overwrite the first element of the list):
    selected_id = file_ids[0].slice();

    // get inputs from the URL passed in:
    var in_url = window.location.search;
    // if there are inputs, on the url, read them:
    if (in_url.length > 0) {
      var parms = in_url.split(url_separator);
      parms[0]=parms[0].substring(1); // strip of beginning '?'
      // if there are the right number of & separated inputs, then use them:
      if (parms.length == selected_id.length + 1){
        if (url_type == 'int'){
          // the url has integers which directly set the selected_id:
          for (var i_ind=0, l_ind=selected_id.length; i_ind < l_ind; i_ind++){
            // when the id integer is passed in the url:
            selected_id[i_ind] = parseInt(parms[i_ind]);
          }
        } else {
          // the url has text which needs decoding:
          for (var i_ind=0, l_ind=selected_id.length; i_ind < l_ind; i_ind++){
            for (i_val=0, l_val=key_lists[i_ind].list.length; i_val < l_val; i_val++){
              if (parms[i_ind] == convertToSlug(key_lists[i_ind].list[i_val].label) ){
                selected_id[i_ind] = i_val;
                break
              }
            }
          }
        }
      }
    }
  }

  //////////////////////////////////////////////////////////////////////
  // writes all of the selectors, to change the selected_id, filtering the available 
  // options so that options in the lower level lists are only presented if they
  // are consistent with the selection at a higher level:
  function write_selectors(level){
    // loop over the selectors needed for the page:
    for (var i_sel=level, l_sel=key_to_selector.length; i_sel < l_sel; i_sel++){
      // firstly, wipe it:
      wipe_dijits_by_div( key_to_selector[i_sel] )
      // then write it:
      write_a_selector(key_lists[i_sel].list, key_to_selector[i_sel], selector_widths[i_sel], selected_id[i_sel], i_sel)
      // if the selector is animated, then set up the animator to point to it:
      if (i_sel == anim_sel){
        write_animator(i_sel);
      }
    }
//    console.log('ALL SELECTORS WRITTEN')
//    console.log('//////////////////////////////////////////////////////////////////////')
  }

  /////////////////////////////////////////////////////////////////////
  // function to destroy dijits on a div...
  function wipe_dijits_by_div(div) {
    //dijit.byId(div).destroyRecursive(true); // not quite right.. ends up with a garbled first element left over from the original...
    dojo.empty(div)// kills it, but still leaves it registered...
    dijit.registry.remove(div)// this unregisters it...
    dijit.registry.remove(div + "_menu") // and this is needed too...
  };

  //////////////////////////////////////////////////////////////////////
  // writes a specific selector, given a list of keys and a target div/span:
  function write_a_selector(list, target, input_width, value, level){
    var _ = document.getElementById(target)

    if (level == 0){
      tmp_list = list;
    } else {
      var filtered = filter_list_by_id(list, level);
      tmp_list = filtered[0];
      tmp_inds = filtered[1];

      // if the selected_id for this level isn't in tmp_inds, then it needs resetting:
      if (tmp_inds.indexOf(selected_id[level]) == -1){
        selected_id[level] = tmp_inds[0]
      }
    }

    // is the width input valid?
    if (input_width === ''){
      sel_width="350px";
    } else {
      sel_width=input_width;
    }

    // set up as Memory
    var key_store = new Memory({
      data : tmp_list
    });
 
    // now as an ObjectStore
    var key_os = new ObjectStore({
      objectStore : key_store
    });

    // now set up the dijit:
    var key_dij = new Select({
      store : key_os,
      value : value,
      title : target,
      width : sel_width,
      height : "30px",
      sortByLabel : false}, target);
    key_dij.startup();

    // and setup what happens when it's changed:
    key_dij.on("change", function() {
      // pick up on the new value for the selected id (but dont show the image):
      change_selected_image(level, this.get("value"), false)
      // and need to reset the other dijits, filtering appropriately, which may change the image we end up with:
      write_selectors(level)
      // now finally, show the image:
      change_selected_image(level, this.get("value"), true)

    });

  }

  //////////////////////////////////////////////////////////////////////
  // writes a set of animation controls to the animator div, which controls stepping
  // through a particular selector:
  function write_animator(i_sel){
    // a pair of buttons that each call a stepping function:
    animator_content1 = "<button onclick='animator_step_back()'>Step back</button>"
    animator_content2 = "<button onclick='animator_step_forward()'>Step forward</button>";
    // and set the content of the div that holds the URL:
    var _1 = document.getElementById("animator1")
    _1.innerHTML = animator_content1;
    var _2 = document.getElementById("animator2")
    _2.innerHTML = animator_content2;
  }

  //////////////////////////////////////////////////////////////////////
  // changes the selected id, at a given level, to the new value (and displays the selected image):
  function change_selected_image(level, value, show){
    // change the value:
    selected_id[level] = value;
    // and show if required:
    if (show){
      set_img_from_id();
    }
  }

  //////////////////////////////////////////////////////////////////////
  // filters an input list, to remove elements that are not possible due to selections at
  // lower levels in the select_id. This routine is the actual workhorse that makes the page work,
  // and is where optimisations are probably needed most.
  function filter_list_by_id(list, level){

    var out_list = new Array;
    var out_inds = new Array;

    // loop over the items we need to check:
    //var item_matches = new Array(list.length).fill(false);
    var item_matches = new Array(list.length);
    for (var i_item=0, l_items=list.length; i_item < l_items; i_item++){item_matches[i_item] = false;}


    // check to see if the selected_id, up to but not including level, matches file's ids, to that level:
    sel_slice = selected_id.slice(0,level);

    // loop through the ids in file_list, to see if any match the current item (up to the level we are at)
    for (var i_file=0, l_files=file_list.length; i_file < l_files; i_file++){

      file_slice = file_ids[i_file].slice(0,level);
      //console.log(selected_id, ':', sel_slice);
      //console.log(file_ids[i_file], ':', file_slice);
      //console.log(file_ids[i_file][level], list[i_item].id )

      // the item in question for this list is:
      var i_item = file_ids[i_file][level];
      // only check items that haven't already been matched:
      if (! item_matches[i_item] ){
        if ( sel_slice.compares(file_slice) ){
           //console.log('selected id: ', selected_id, 'matched file_id:', file_ids[i_file], ' at level', level, sel_slice, file_slice)
           item_matches[i_item]=true;
        }
      }
    }

    for (var i_item=0, l_items=list.length; i_item < l_items; i_item++){
      if (item_matches[i_item]){
         out_list = out_list.concat(list[i_item]);
         out_inds = out_inds.concat(i_item);
      }
    }

    //console.log(['level:', level, 'item_matches:', item_matches])
    //console.log(['list:', list])
    //console.log(['out_list:', out_list])

    return [out_list, out_inds]
  }


}) // ends the require([...]{})

// All functions for the animator buttons, and routines these call, need to be outside the require()
//

//////////////////////////////////////////////////////////////////////
// sets the image to the URL, according to the selected_id:
function set_img_from_id() {
  // set the string to use the the_image div:
  var the_file = '<p>Sorry, there is no image for that selection.</p>'
  //
  for(var file_ind=0, len=file_list.length;  file_ind < len; file_ind++) {
    // compare the arrays, using the array compare method we added earlier:
    //alert([file_list[file_ind].id, ':', selected_id])
    if ( selected_id.compares( file_ids[file_ind]) ){
      // set the file, and break the loop:
      the_file = "<p><img src=" + file_list[file_ind] + "></p>"
    }
  }
  // now set the_image div:
  var _ = document.getElementById("the_image")
  _.innerHTML = the_file;
  // display the URL to this page:
  write_url_to_div()
}

///////////////////////////////////////////////////////////////////////
// converts text to text suitable to be used in a URL (a slug):
function convertToSlug(Text){
  return Text
      .toLowerCase()
      .replace(/[^\w ]+/g,'')
      .replace(/ +/g,'-')
      ;
}

/////////////////////////////////////////////////////////////////////
// sets the URL to the page in the div:
function write_url_to_div() {
  // split on question mark: stuff after this is a javascript input:
  qm_split = document.location.toString().split('?');
   // split up the frame url, with '/'
  frame_slashes = qm_split[0].split('/')
  //alert(frame_slashes);
   // construct the output url:
  if (tab_name.localeCompare('None')){out_url = pagename +'?'+ tab_name + url_separator}
  else {out_url = pagename +'?'}
      
  // add the new page's script inputs onto the end, according to the required format:
  if (url_type == 'int'){
    // output url just has integers, directly setting the selected_id:
    for (var i_ind=0; i_ind<selected_id.length; i_ind++){
      out_url = out_url + selected_id[i_ind].toString() + url_separator ;
    }
  } else {
    for (var i_ind=0; i_ind<selected_id.length; i_ind++){
      // outputs the url as text:
      out_url = out_url + convertToSlug(key_lists[i_ind].list[selected_id[i_ind]].label) + url_separator;
    }
  }

  // and pre-pending the actual address:
  for (var i_slash=frame_slashes.length-2; i_slash>=0; i_slash--){
  out_url = frame_slashes[i_slash]+"/"+out_url;
  }
  // and set the content of the div that holds the URL:
  var _ = document.getElementById("the_url")
  _.innerHTML = "<p>To link to this page use this URL: <a href="+out_url+" target=_top>"+out_url+"</a></p>";
}

//////////////////////////////////////////////////////////////////////
// function called by the animator stepping backwards one:
function animator_step_back(){
  // look for the next selected id:
  step_selected_id(-1 * anim_dir)
  // now we have a new selected_id, refresh the selectors, image and url:
  // display the URL to this page:
  write_url_to_div()
  // display the image that relates to the initial selected_id:
  set_img_from_id()
  // now write out the different selectors, from number/level 0:
  // At present, this is not done, as the write_selectors need to be in the 
  // require section, so are done at the start... perhaps 
  // I can refresh their values instead? Look into that another time!
  //write_selectors(0)
}
//////////////////////////////////////////////////////////////////////
// function called by the animator stepping backwards one:
function animator_step_forward(){
  // look for the next selected id:
  step_selected_id(1 * anim_dir)
  // now we have a new selected_id, refresh the selectors, image and url:
  // display the URL to this page:
  write_url_to_div()
  // display the image that relates to the initial selected_id:
  set_img_from_id()
  // now write out the different selectors, from number/level 0:
  // At present, this is not done, as the write_selectors need to be in the 
  // require section, so are done at the start... perhaps 
  // I can refresh their values instead? Look into that another time!
  //write_selectors(0)
}

//////////////////////////////////////////////////////////////////////
// function to step through to the next selected_id
function step_selected_id(incr){

  // how many values are there in the selector in question?
  // when we get to this number, the value needs to go to zero:
  max_val_for_sel = key_lists[anim_sel].list.length -1;
  // the min_val is zero, of course...

  // going to try differnt 'id' arrays, varying
  // the element in anim_sel:
  starting_val = selected_id[anim_sel];
  test_id = selected_id;
  test_id[anim_sel] = starting_val + incr;
  if (test_id[anim_sel] < 0){test_id[anim_sel]=max_val_for_sel;}
  if (test_id[anim_sel] > max_val_for_sel){test_id[anim_sel]=0;}

  var got_new_id = false;
  while (test_id[anim_sel] != starting_val){
    // test to see if this value if valid for the other selectors...
    for(var file_ind=0, len=file_list.length;  file_ind < len-1; file_ind++) {
      // now compare the arrays test_id and file_list[file_ind].id
      if (test_id.compares(file_ids[file_ind])){
        // we have a winner! (do a slice, so it takes a copy, rather than moving it through in the loop)
        selected_id = file_ids[file_ind].slice()
        // set the test_val so that, after incrementing, it stops the loop:
        test_id[anim_sel] = starting_val - incr;
        got_new_id = true;
        break
      }
    }
    // increment the test_val
    test_id[anim_sel] += incr;
    if (test_id[anim_sel] < 0){test_id[anim_sel]=max_val_for_sel;}
    if (test_id[anim_sel] > max_val_for_sel){test_id[anim_sel]=0;}
  }
  
  // if we didn't get an exact match, then we need to look again and try to find a close-ish one:
  //if (!got_new_id){
  //  console.log('failed to find an exact match');
  //}
}

</script>
''')
    
def write_js_placeholders(file_obj=None, dict_depth=None, selector_prefix=None, style='horiz dropdowns'):
    '''
    write the final details (which is the stuff that actually gets read!) at the end of a tab
    containing stdout stuff to a file object
    '''

    #if not isinstance(file_obj, file):
    #    print type(file_obj)
    #    raise ValueError('The file_obj passed into PlotDictionary.write_js must be an open file object.')

    if selector_prefix is None:
        selector_prefix, junk1, junk2 = write_js_setup_defaults()

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
    
