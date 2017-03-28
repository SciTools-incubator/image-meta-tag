// ImageMetaTag dropdown menu scripting - vn0.5
// (C) Crown copyright Met Office. All rights reserved.
// Released under BSD 3-Clause License.

function read_parse_json_files(json_files, lzunpack){
    // reads a list of files that contain the json 
    // data structure. The files can be compressed
    // using lzstring compression, in which case they
    // might also be split into sections.
    var json_str = '';
    for (var i_js=0; i_js < json_files.length; i_js++){
	var this_str = readTextFile(json_files[i_js]);
	if (lzunpack){
	    json_str += LZString.decompressFromUTF16(this_str);
	} else {
	    json_str += this_str;
	};
    };
    json = JSON.parse(json_str);
    return json
}

function readTextFile(filepath){
    // reads a text file and returns the content:
    var request = new XMLHttpRequest();
    request.open("GET", filepath, false);
    request.send(null);
    var returnValue = request.responseText;
    return returnValue;
}

function imt_main () {
    // main function, run on load:
    // parse the input url to see if it overides the default selection above
    get_selection();
    // validate that selection:
    validate_selected_id(0);
    // use that selection:
    apply_selection(0);
    // add the animation buttons
    if (anim_sel >= 0) {add_animators();}
}

function get_selection () {
    // get inputs from the URL passed in:
    //console.log("Checking contents of an input URL")
    var in_url = window.location.search;
    //console.log(in_url)
    // if there are inputs, on the url, read them:
    if (in_url.length > 0) {
        var parms = in_url.split(url_separator);
        parms[0]=parms[0].substring(1); // strip of beginning "?"
        // if there are the right number of & separated inputs, then use them:
        if (parms.length == n_deep + 1){
            if (url_type == "int"){
                // the url has integers which directly set the selected_id:
                for (var i_ind=0; i_ind < n_deep; i_ind++){
                    // when the id integer is passed in the url:
                    selected_id[i_ind] = parseInt(parms[i_ind]);
                }
            } else {
                // the url has text which needs decoding:
                for (var i_ind=0, l_ind=selected_id.length; i_ind < l_ind; i_ind++){
                    for (i_val=0, l_val=key_lists[i_ind].length; i_val < l_val; i_val++){
                        if (parms[i_ind] == convertToSlug(key_lists[i_ind][i_val])){
                            selected_id[i_ind] = i_val;
                            break;
                        }
                    }
                }
            }
        }
    } else if (selected_id.length == 0) {
        // we don't have an input id, so take the first workable image
        alert("The page is corrupted, selected_id has zero length.");
    }
}

function apply_selection (start_depth) {
    // function to run when a selection has been made
    //console.log("at start of apply_selection, selectid_id:", selected_id)
    //console.log("apply_selection:", selected_id)
    // populate the available options, at each depth, for the current selection:
    var options_at_depth = [];
    var selected_at_depth = [];
    // run through the selections, finding the end destination, and the selections available at each level
    for (var i_d=0; i_d < n_deep; i_d++){
        // at this i_d, what is the selected key:
        var selected_key = key_lists[i_d][selected_id[i_d]];
        // now subset the imt data strcuture, based on what is selected,
        // so we can move on to the next level:
        if (i_d == 0){
            // store what keys are available at this i_d:
            var keys_at_depth = Object.keys(imt);
            //console.log("imt: ", imt)
            //console.log("selected_key: ", selected_key)
            // and proceed to subset, for the next level deeper:
            var imt_subset = imt[selected_key];
            //console.log(imt_subset)
        } else {
            var keys_at_depth = Object.keys(imt_subset);
            imt_subset = imt_subset[selected_key];
        }
        // and make a note of what valid options are available to
        options_at_depth[i_d] = sorted_by(keys_at_depth, key_lists[i_d]);
        selected_at_depth[i_d] = selected_key;
        // for the animator buttons, we need to keep the indices of the valid options
        // to cycle through:
        if (i_d == anim_sel){
            anim_options = [];
            for (i_opt=0, n_opts=options_at_depth[i_d].length; i_opt < n_opts; i_opt++) {
                //console.log(".....")
                //console.log(options_at_depth[i_d][i_opt])
                //console.log(key_lists[i_d])
                //console.log(key_lists[i_d].indexOf(options_at_depth[i_d][i_opt]))
                //console.log(".....")
                // append the index, in key_lists, of the current option
                anim_options.push(key_lists[i_d].indexOf(options_at_depth[i_d][i_opt]))
                    // make a note if this is the current selection:
                    if (options_at_depth[i_d][i_opt] == selected_key){
                        anim_ind = i_opt;
                    }
            }
        }
    }
    // if we have got here then we actually have the payload
    apply_payload(imt_subset);
    // write the selectors, to change the next page
    update_selectors(options_at_depth, selected_at_depth, start_depth);
    // write out the url
    write_url_to_div();
}

function apply_payload( payload ) {
    // applies the payload of the selected image(s) to the_image:
    // set the string to use the the_image div:
    var the_file = "<p>Sorry, there is no image for that selection.</p>";
    // set the file, and break the loop:
    if (Array.isArray(payload)){
        // the right number of rows for a squarish box is the floor of the square root of the number of images:
        var n_imgs = payload.length;
        if (n_imgs <= 3){
            var n_cols = n_imgs;
            //var n_rows = 1;
        } else {
            var n_cols = Math.ceil(Math.sqrt(n_imgs));
            //var n_rows = Math.ceil(n_imgs / n_cols);
        }
        //the_file = "An array of " + n_imgs.toString() + " files goes here";
        //the_file += ", in " + n_rows.toString() + " rows";
        //the_file += " and " + n_cols.toString() + " columns";
        // TODO: sort out the screen width and set the image widths appropriately, so itfits the screensize:
        the_file = "<p><table cellspacing=2>";
        for (var i_img=0; i_img < n_imgs; i_img++){
            if (i_img % n_cols == 0){ the_file += "<tr>"}
            the_file += "<td><img src=" + payload[i_img] + "></td>";
        }
        the_file += "</table></p>";
    } else {
        the_file = "<p><img src=" + payload + "></p>";
    }
    // now set the_image div:
    var _ = document.getElementById("the_image");
    _.innerHTML = the_file;
}

function update_selectors(options_at_depth, selected_at_depth, start_depth) {
    // updates the selectors with the choices valid for the current selection
    for (var depth=start_depth, len=options_at_depth.length; depth < len; depth++){
        // rewrite the selector for this depth:
        update_selector(depth, options_at_depth[depth], selected_at_depth[depth]);
    }
}

function update_selector(depth, options, selected) {
    // updates a selector at a particular depth, with a set of options
    // and the selected value as the current selection:
    target_div = key_to_selector[depth];
    //console.log("updating sel", depth);
    //console.log("  at div", target_div);
    //console.log("  with options", options);
    //console.log("  and selected val", selected);

    // set up the text to define the selector:
    sel_text = "<select id='select_"+ depth
        sel_text += "' onChange='OnSelected("+ depth +")'>\n"
        for (var i_opt=0, len=options.length; i_opt < len; i_opt++){
            // loop over the options, and write out a line for each one:
            for (var j_opt=0, len_j=key_lists[depth].length; j_opt < len_j; j_opt++){
                // first, get the index in key_lists[depth] to which i_opt refers
                // as not every option is used in every selection:
                if (key_lists[depth][j_opt] == options[i_opt]){break};
            }
            if (options[i_opt] == selected){
                sel_text += "  <option value=" + j_opt + " selected=selected>"+options[i_opt]+"</option>\n"
            } else {
                sel_text += "  <option value=" + j_opt + ">"+options[i_opt]+"</option>\n"
            }
        }
    // finish it off:
    sel_text += "</select>"

        // now set the sel div:
        var _ = document.getElementById("sel"+depth)
        _.innerHTML = sel_text;
    //console.log(sel_text)
}

function OnSelected(depth){
    // acts to apply the selection changes for a given selector
    //console.log("OnSelected depth:", depth);
    new_value = document.getElementById("select_"+depth).value;
    //console.log(selected_id);
    selected_id[depth] = parseInt(new_value);
    //console.log(selected_id);
    validate_selected_id(depth+1);
    //console.log(selected_id);
    apply_selection(0);
}

function validate_selected_id(start_depth) {
    // validates that a selected_id is valid, starting from a given depth
    //console.log("validating from depth: ", start_depth)
    // first of all, get the imt information, subsetted to the start_depth
    //console.log(start_depth)
    if (start_depth == 0) {
        var imt_subset = imt;
    } else {
        for (var i_d=0; i_d < start_depth; i_d++){
            var selected_key = key_lists[i_d][selected_id[i_d]];
            if (i_d == 0){
                var imt_subset = imt[selected_key];
            } else {
                imt_subset = imt_subset[selected_key];
            }
        }
    }
    //console.log("imt_subset, validation:", imt_subset)
    for (var i_d=start_depth; i_d < n_deep; i_d++){
        // at this i_d, what is the selected key:
        var selected_key = key_lists[i_d][selected_id[i_d]]
            // now subset the imt data strcuture, based on what is selected,
            keys_this_depth = Object.keys(imt_subset)
            //console.log(keys_this_depth, selected_key)
            //console.log(keys_this_depth.indexOf(selected_key))
            if (keys_this_depth.indexOf(selected_key) == -1){
                // the currently held selection is NOT valid, so replace it:
                //
                // TODO: sometimes there might be a requirement to do
                // more clever stuff here. For now:
                // find from the sorted list of valid options:
                keys_this_depth = sorted_by(keys_this_depth, key_lists[i_d])
                // and pick the first one:
                selected_key = keys_this_depth[0]
                // and change the selected_id to point to it:
                selected_id[i_d] = key_lists[i_d].indexOf(selected_key)
            }
        // the selected_id is valid for the previous selections, so subset imt and proceed:
        imt_subset = imt_subset[selected_key]
            }
}

function sorted_by(in_list, order_list) {
    // sorts an in_list accoring to an order_list
    out_list = [];
    order_list.forEach(function(key) {
       var found = false;
       in_list = in_list.filter(function(item) {
               if(!found && item == key) {
                   out_list.push(item);
                   found = true;
                   return false;
               } else {
                   return true;
               }
           })
    })
    //console.log("sorted list: ", out_list)
    return out_list
}

function write_url_to_div() {
    // sets the URL to the page in the div:
    //
    // split on question mark: stuff after this is a javascript input:
    qm_split = document.location.toString().split("?");
    // split up the frame url, with "/"
    frame_slashes = qm_split[0].split("/");
    //alert(frame_slashes);
    // construct the output url:
    if (tab_name.localeCompare("None")){
        out_url = pagename +"?"+ tab_name + url_separator;
    }
    else {
        out_url = pagename +"?";
    }
    // add the new page's script inputs onto the end, according to the required format:
    if (url_type == "int"){
        // output url just has integers, directly setting the selected_id:
        for (var i_ind=0; i_ind < n_deep; i_ind++){
            out_url = out_url + selected_id[i_ind].toString() + url_separator ;
        }
    } else {
        for (var i_ind=0; i_ind<selected_id.length; i_ind++){
            // outputs the url as text:
            //console.log(i_ind, key_lists[i_ind], selected_id[i_ind])
            out_url = out_url + convertToSlug(key_lists[i_ind][selected_id[i_ind]]) + url_separator;
        }
    }
    if (!show_rel_url){
        // and pre-pending the actual address:
        for (var i_slash=frame_slashes.length-2; i_slash>=0; i_slash--){
            out_url = frame_slashes[i_slash]+"/"+out_url;
        }
    }
    // and set the content of the div that holds the URL:
    var _ = document.getElementById("the_url");
    _.innerHTML = "<p>To link to this page use this URL: <a href="+out_url+" target=_top>"+out_url+"</a></p>";
}

function convertToSlug(Text){
    // converts text to text suitable to be used in a URL (a slug):
    return Text
        .toLowerCase()
        .replace(/[^\w ]+/g,'')
        .replace(/ +/g,'-')
        ;
}

function add_animators() {
    // adds in the appropriate text to the animator buttons:
    //
    // a pair of buttons that each call a stepping function:
    animator_content1 = "<button onclick='animator_step_back()'>Step back</button>";
    animator_content2 = "<button onclick='animator_step_forward()'>Step forward</button>";
    // and set the content of the div that holds the URL:
    var _1 = document.getElementById("animator1");
    _1.innerHTML = animator_content1;
    var _2 = document.getElementById("animator2");
    _2.innerHTML = animator_content2;
}

function animator_step_back(){
    // animator, stepping backwards:
    // look for the next selected id:
    step_selected_id(-1 * anim_dir);
    // validate from the change:
    validate_selected_id(anim_sel+1);
    // use that selection:
    apply_selection(0);
}
function animator_step_forward(){
    // animator, stepping forwards:
    // look for the next selected id:
    step_selected_id(1 * anim_dir);
    // validate from the change:
    validate_selected_id(anim_sel+1);
    // use that selection:
    apply_selection(0);
}
function step_selected_id(incr){
    // function to step through to the next selected_id
    var current_ind = anim_options.indexOf(selected_id[anim_sel]);
    var new_ind = current_ind + incr;
    if (new_ind < 0){
        new_ind = anim_options.length -1;
    } else if (new_ind >= anim_options.length){
        new_ind = 0;
    }
    selected_id[anim_sel] = anim_options[new_ind];
}
