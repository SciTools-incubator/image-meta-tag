'''
Submodule containing an ImageDict class, and function for preparing them.

@author: Malcolm.E.Brooks@metoffice.gov.uk
'''
# required imports
import Image, os, re, collections
# useful for debugging
import pdb

from copy import deepcopy
from itertools import islice
from math import ceil

class ImageDict():
    '''
    A class which holds a heirachical dictionary of dictionaries, and the associated
    methods for appending/removing dictionaries from it.
    
    The expected use case for the dictionary is to represent a large set of images, 
    which can be organised by their metadata tags.
    
    When used in this way, the ImageDict class also contains methods which write out
    web page interfaces for browsing the images. 

    '''
    def __init__(self, input_dict, full_name_mapping=None,
                 selector_widths=None, selector_animated=None,
                 animation_direction=None):
        # set the dictionary:
        self.dict = input_dict
        # now list the keys, at each level, as lists. These can be reorderd by the calling routine,
        # so when the dictionary is written out, they can be in the desired order: 
        self.keys = self.list_keys_by_depth()
        
        dict_depth = self.dict_depth()
        
        if full_name_mapping is None:
            self.full_name_mapping = None
        else:
            if not isinstance(full_name_mapping, dict):
                raise ValueError('A mapping of key names to full names has been supplied, but it is not a dictionary')
            else:
                self.full_name_mapping = full_name_mapping
        
        # this controls the width of the selector, on the resultant webpage:        
        if selector_widths is None:
            self.selector_widths = [""] * dict_depth
        else:
            if not isinstance(selector_widths, list):
                raise ValueError('Specified selector_widths should be a list, but it is "%s" instead' % selector_widths)
            if len(selector_widths) != self.dict_depth():
                raise ValueError('Specified selector_widths length disagrees with the dictionary depth')
                
            self.selector_widths = selector_widths
        # this controls whether or not a particualr selector uses the animation controls or not.
        # There can be only one per page, default is that none use it...
        if selector_animated is None:
            self.selector_animated = -1
        else:
            if not isinstance(selector_animated, int):
                raise ValueError('Specified selector_animated should be a single integer')
            if selector_animated < -1 or selector_animated >= self.dict_depth():
                raise ValueError('selector_animated (%s) is out of range of the plot dictionary depth.' % selector_animated)
            # that passes, so store it:
            self.selector_animated = selector_animated
        
        if animation_direction is None:
            self.animation_direction = 1
        else:
            if not isinstance(animation_direction, int) or (animation_direction != 1 and animation_direction != -1):
                msg = 'Specified animation_direction should be a single integer with values +1 or -1, '
                msg += 'but it is "%s" instead' % animation_direction
                raise ValueError(msg)
            self.animation_direction = animation_direction
          
    def __repr__(self):
        outstr = 'ImageMetaTag ImageDict:\n'
        outstr = self.dict_print(self.dict, indent=1, outstr=outstr)
        return outstr
    
    def append(self, new_dict, devmode=False, skip_key_relist=False):
        '''
        appends a new dictionary (with a single element in each layer!) into a current ImageDict
        The skip_key_relist option can be set to True to stop the regeneration of key lists.
        '''
        if isinstance(new_dict, ImageDict):
            merged_dict = dict( self.mergedicts(self.dict, new_dict.dict) )
            self.dict = merged_dict
        elif isinstance(new_dict, dict):
            merged_dict = dict( self.mergedicts(self.dict, new_dict) )
            self.dict = merged_dict
        else:
            raise ValueError('Cannot append data type %s to a ImageDict' % type(new_dict))
        
        if not skip_key_relist:
            self.keys = self.list_keys_by_depth(devmode=devmode)
        # TODO: if there is a full_name_mapping, check that the new item hasn't added something to it
        
    def dict_union(self, in_dict, new_dict):
        'produces the union of a dictionary of dictionaries'
        for key, val in new_dict.iteritems():
            if not isinstance(val, dict):
                in_dict[key] = val
            else:
                subdict = in_dict.setdefault(key, {})
                self.dict_union(subdict, val)

    def mergedicts(self, dict1, dict2):
        '''alternative version of dict_union using generators which is much faster for large dicts
        but needs to be converted to a dict when it's called: new_dict = dict(mergdicts(dict1,dict)) '''
        for k in set(dict1.keys()).union(dict2.keys()):
            if k in dict1 and k in dict2:
                if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                    yield (k, dict(self.mergedicts(dict1[k], dict2[k])))
                else:
                    # If one of the values is not a dict, you can't continue merging it.
                    # Value from second dict overrides one in first and we move on.
                    yield (k, dict2[k])
                    # Alternatively, replace this with exception raiser to alert you of value conflicts
            elif k in dict1:
                yield (k, dict1[k])
            else:
                yield (k, dict2[k])
                
    def remove(self, rm_dict, skip_key_relist=False):
        '''
        removes a dictionary from within an ImageDict.
        The skip_key_relist option can be set to True to stop the regeneration of key lists.
        
        TIP: Because the remove process needs to prune empty sections afterwards, it can be slow.
        When working with large dictionaries, and removing a large number of elements from it, is often faster
        to build up a dictionary of things you want to remove, and then do one remove at the end.
        '''
       
        # delete the items in question from the dictionary - this can leave empty branches of the dictionary though:
        if isinstance(rm_dict, ImageDict):
            self.dict_remove(self.dict, rm_dict.dict)
        elif isinstance(rm_dict, dict):
            self.dict_remove(self.dict, rm_dict)
        else:
            raise ValueError('Cannot remove data type %s from a ImageDict' % type(rm_dict))
        # now prune empty branches away:
        dicts_to_prune = True
        while dicts_to_prune:
            dicts_to_prune = self.dict_prune(self.dict)
        # relist the keys:
        if not skip_key_relist:
            self.keys = self.list_keys_by_depth()
        
        # TODO: if there is a full_name_mapping, check that the new item hasn't removed something to it
    
    def dict_remove(self, in_dict, rm_dict):
        '''
        removes a dictionary of dictionaries from another, larger, one. 
        This can leave empty branches, at multiple levels of the dict, so needs cleaning up afterwards.
        '''
        for key, val in rm_dict.iteritems():
            if isinstance(val, dict):
                # descend further up into the dictionary tree structure:
                self.dict_remove(in_dict.setdefault(key, {}), val)
            else:
                # if the key is in the in_dict at this level, remove it:
                if key in in_dict.keys():
                    in_dict.pop(key)                   

    def dict_prune(self, in_dict, dicts_pruned=False):
        '''
        prunes the ImageDict of empty, unterminated, branches (which occur after parts have been removed).
        Returns True if a dict was pruned, False if not.
        '''
        pop_list = []
        for key, val in in_dict.iteritems():
            if isinstance(val, dict):
                # descend further up into the dictionary tree structure:
                if len(val.keys()) > 0:
                    dicts_pruned = self.dict_prune(val, dicts_pruned=dicts_pruned)
                else:
                    pop_list.append(key)
                    dicts_pruned = True
            elif val is None:
                pop_list.append(key)
                dicts_pruned = True
        # now do the prune:
        for key in pop_list:
            in_dict.pop(key)

        return dicts_pruned
      
    def dict_print(self, in_dict, indent=0, outstr=''):
        'recursively details a dictionary of dictionaries, with indentation, to a string'
        n_spaces = 2 # number of spaces to indent, per level
        
        #for key, value in in_dict.iteritems():
        # loop over the defined list of keys, to present in them in the current sorted order.
        for key in self.keys[indent-1]:
            value = in_dict[key]
            outstr = '%s%s%s:\n' % (outstr, ' '*indent*n_spaces, key)
            if isinstance(value, dict):
                outstr = self.dict_print(value, indent=indent+1, outstr=outstr)
            else:
                outstr = '%s%s%s\n' % (outstr, ' '*(indent+1)*n_spaces, value)
        return outstr
    
    def dict_depth(self, uniform_depth=False):
        '''uses dict_depths to get the depth of all branches of the plot_dict and, 
        if required, checks they all equal the max'''
        #  get the depth of all trees of the dict, and flatten the list:
        dict_depths = [d for d in self.flatten_lists( self.dict_depths(self.dict) )]
        # find the max:
        dict_depth = max(dict_depths)
        # and check its uniformity if required:
        if uniform_depth:
            # check the dictionary depth is uniform_depth for all elements, and raise an error if not 
            if len(set(dict_depths)) != 1:
                raise ValueError, 'Plot Dictionary is of non uniform depth and uniform_depth=True has been specified'
        return dict_depth
    
    def dict_depths(self, in_dict, depth=0):
        'recursively finds the depth of a ImageDict and returns a list of lists'
        if not isinstance(in_dict, dict) or not in_dict:
            return depth
        return [self.dict_depths(next_dict, depth+1) for (next_key, next_dict) in in_dict.iteritems()]
    
    def flatten_lists(self, in_list):
        'recursively flattens a list of lists:'
        for list_element in in_list:
            if isinstance(list_element, collections.Iterable) and not isinstance(list_element, basestring):
                for sub_list in self.flatten_lists(list_element):
                    yield sub_list
            else:
                yield list_element
    
    def list_keys_by_depth(self, devmode=False):
        'converts the sets, from keys_by_depth to a list (where they can be ordered and indexed)'
        keys = self.keys_by_depth(self.dict)

        out_keys = {}
        for level in keys.keys():
            # convert to a list:
            out_keys[level] = list(keys[level])
            # and sort HERE:
            out_keys[level] = sorted(out_keys[level])
            
        return out_keys

    def keys_by_depth(self, in_dict, depth=0, keys=None):
        'returns a dictionary of sets, containing the keys at each level of the dictionary (keyed by the level number)'
        if keys is None:
            keys = {}
        if not depth in keys:
            keys[depth] = set()
        for key in in_dict:
            keys[depth].add(key)
            if isinstance(in_dict[key], dict):
                self.keys_by_depth(in_dict[key], depth+1, keys)
        return keys
       
    def key_at_depth(self, dct, dpt):
        'returns the keys of a dictionary, at a given depth'
        if dpt > 0:
            return [ key for subdct in dct.itervalues() for key in self.key_at_depth(subdct, dpt-1)  ]
        else:
            return dct.keys()
    
    def return_key_inds(self, in_dict, out_array=None, this_set_of_inds=None, 
                        depth=None, level=None, verbose=False, devmode=False):
        '''
        does the work for dict_index_array, by recursively adding indices to the keys to a current list, 
        and branching where required, and adding compelted lists to the out_array
        '''
        for key, value in in_dict.iteritems():
            if verbose:
                print 'IN: level: %s, before changes: %s, key "%s" in %s' % (level, this_set_of_inds, key, self.keys[level] )
            
            if isinstance(value, dict):
                # make a note of which key it is:
                
                if key in self.keys[level]:
                    # we've moved up a level from the previous one, make a note of the new value at the new level 
                    this_set_of_inds[level] = self.keys[level].index(key)
                    # increment the level, in case the next dict is at the higher level in the tree structure:
                    level += 1
                    if verbose:
                        print 'new setting: %s' % this_set_of_inds
                        print 'out_array: %s' % out_array
                    # and recurse:
                    self.return_key_inds(value, out_array=out_array, 
                                         this_set_of_inds=this_set_of_inds, depth=depth, level=level)
                elif key in self.keys[level-1]:
                    # the dictionary we've now got isn't at a higher level than before, which means 
                    # we're traversing the level from the previous call.
                    # record the new index on a copy, and then recursively carry on:
                    branched_level = deepcopy(level)
                    branched_set_of_inds = deepcopy(this_set_of_inds) 
                    branched_set_of_inds[branched_level-1] = self.keys[branched_level-1].index(key)
                    
                    if verbose:
                        print 'new setting: %s' % this_set_of_inds
                        print 'out_array: %s' % out_array
                    # and recurse:
                    self.return_key_inds(value, out_array=out_array, 
                                         this_set_of_inds=branched_set_of_inds, depth=depth, level=branched_level)
                    
                else:
                    # we really shouldn't be here:
                    raise ValueError('Error recursing through dict: key "%s" not found in this level, or one below' % key)
                
            else:
                # we're at the top level of the tree, record the index:
                if key in self.keys[level]:
                    # we've moved up a level from the previous one, make a note of the new value at the new level 
                    this_set_of_inds[level] = self.keys[level].index(key)
                #elif level == 0:
                #    # wer're traversing the top level of the dictionary, so level has been set to zero:
                #    this_set_of_inds[-1] = self.keys[depth-1].index(key)
                else:
                    # again, we shouldn't ever get here:
                    if devmode:
                        pdb.set_trace() #@@@
                        print 'stop here' #@@@
                    else:                                                        
                        raise ValueError('Error recursing through the plot dictionary: key not found in top level!')
                
                # we're done, so append this to the out_array, and DON'T recurse:
                out_array.append(deepcopy(this_set_of_inds))
    
    def dict_index_array(self, devmode=False):
        '''
        using the list of dictionary keys (at each level of a uniform_depth dictionary of dictionaries), this
        produces a list of the indices that can be used to reference the keys to get the result for each element...
        '''
        
        # want to build up a list of lists, each giving the indices of the keys that get to a plot:   
        depth = self.dict_depth(uniform_depth=True)
        out_array = []
        this_set_of_inds = [None] * depth
        level = 0
        self.return_key_inds(self.dict, out_array=out_array, 
                             this_set_of_inds=this_set_of_inds, depth=depth, 
                             level=level, devmode=devmode)
        # the recursive method comes out sorted as it iterates about the dictionary, 
        # not as to how the keys are sorted. Easy to do:
        out_array.sort()
       
        return (self.keys, out_array)

    def sort_keys(self, sort_methods, devmode=False):
        '''sorts the keys of a plot dictionary, according to a particular sort method 
        (or a list of sort methods that mathces the number of keys)
        Valid sort methods so far include:
          'sort' - just an ordinary sort
          'reverse sort' - a reversed sort 
          'level' or 'numeric' - starting with the surface and working upwards, then 'special' 
             levels like cross sections etc. 
          'datetime' - datetime...
          'T+' - in ascending order of the T+??? number
          an input list - element in the input list are sorted as per their order in the list,
             while the rest are just sorted.
        '''
        
        if len(sort_methods) != len(self.keys):
            raise ValueError('inconsistent lengths of the sort_methods and the self.keys to sort')
            
        for i_key, method in enumerate(sort_methods):
            if isinstance(method, str):
                # the method is a specified way of sorting:
                if method in ['sort', 'alphabetical']:
                    # - just alphanumeric style sort. 
                    self.keys[i_key].sort()
                    
                elif method in ['reverse sort', 'reverse_sort']:
                    # -a reversed sort
                    self.keys[i_key].sort(reverse=True)
                
                elif method in ['T+', 'reverse T+', 'reversed_T+']:
                    #'T+' - in ascending order of the T+??? number:
                    
                    # get a list of tuples, containing the string, and the value of the T+ from a pattern match regex:
                    try:
                        labels_and_values = [(x, re.match('[tT][+]{,}([0-9.]{1,})|None', x).group(1)) for x in self.keys[i_key]]
                        if method == 'T+':
                            # map the None to a string, so it goes to then end of a sort
                            labels_and_values = [(x, float(y)) if not y is None else (x, 'None') for x, y in labels_and_values]
                        elif method in ['reverse T+', 'reversed_T+']:
                            # don;t map the none to a string, so it goes to the end of a reversed sort...
                            labels_and_values = [(x, float(y)) if not y is None else (x, y) for x, y in labels_and_values]
                    except:
                        msg = 'Keys for plot dictionary level "%s" do not match the "T+" (or None) pattern' % self.keys[i_key]
                        if devmode:
                            print msg
                            pdb.set_trace()
                            print 'stop'
                        else:
                            raise ValueError(msg)            
                    
                    # now either sort, or reverse sort, using the value as the key:
                    if method == 'T+':
                        labels_and_values.sort(key=lambda x: x[1])
                    elif method in ['reverse T+', 'reversed_T+']:
                        labels_and_values.sort(key=lambda x: x[1], reverse=True)
                    # and pull out the labels, in the right order:
                    self.keys[i_key] = [x[0] for x in labels_and_values]
                
                elif method in ['level', 'numeric']:
                    #'level' - starting with the surface and working upwards, then 'special' levels like cross sections etc. 
                    
                    # add to this as keys from self.keys[i_key] are added to it:
                    tmp_keys = []

                    # the surface levels go first:                    
                    surface_levels = ['Surface']
                    for item in surface_levels:
                        if item in self.keys[i_key]:
                            tmp_keys.append(self.keys[i_key].pop( self.keys[i_key].index(item) ))
                        if len(self.keys[i_key]) == 0:
                            break
                    
                    # now anything with a 'm' or 'km' or 'nm' (for wavelenghts!) needs to be sorted, starting with the lowest:
                    # TODO: add more things to this, microns, with the micro as /mu????
                    metre_patterns_and_scalings = [(r'([0-9.eE+-]{1,})[\s]{,}m$', 1.0),
                                                   (r'([0-9.eE+-]{1,})[\s]{,}mm$', 1.0-3),
                                                   (r'([0-9.eE+-]{1,})[\s]{,}microns$', 1.0-6),
                                                   (r'([0-9.eE+-]{1,})[\s]{,}\mum$', 1.0-6),
                                                   (r'([0-9.eE+-]{1,})[\s]{,}nm$', 1.0e-9),
                                                   (r'([0-9.eE+-]{1,})[\s]{,}km$', 1000.0)]
                                                         
                    # now anything with a 'hPa' or 'mb' needs to be sorted, starting with the lowest in height (hieghest value):
                    pressure_patterns_and_scalings = [(r'([0-9.eE+-]{1,})[\s]{,}Pa$', 1.0),
                                                      (r'([0-9.eE+-]{1,})[\s]{,}mb$', 100.0),
                                                      (r'([0-9.eE+-]{1,})[\s]{,}mbar$', 100.0),
                                                      (r'([0-9.eE+-]{1,})[\s]{,}hPa$', 100.0)]
                    
                    model_lev_patterns_and_scalings = [(r'Model level ([0-9]{1,})', 1.0),
                                                       (r'model level ([0-9]{1,})', 1.0),
                                                       (r'Model lev ([0-9]{1,})', 1.0),
                                                       (r'model level ([0-9]{1,})', 1.0),
                                                       (r'ML([0-9]{1,})', 1.0),
                                                       (r'ml([0-9]{1,})', 1.0)]
                    
                    # now anything where the level defines locations, with latt long coordinates:
                    lattlong_patterns_and_scalings = [(r'([0-9.]{1,})E[,\s]{,}[0-9.]{1,}N', 1.0)]
                    
                    # now anything else with a numeric value:
                    numeric_patterns_and_scalings = [(r'([0-9.eE+-]{1,})', 1.0)]
                    
                    # now loop through the different patterns/scalings, and their orders:
                    pattern_order_loop = [(metre_patterns_and_scalings, 'sort'), 
                                          (pressure_patterns_and_scalings, 'reversed'),
                                          (model_lev_patterns_and_scalings, 'sort'),
                                          (lattlong_patterns_and_scalings, 'sort'),
                                          (numeric_patterns_and_scalings, 'sort') ]
                    
                    for patterns_scalings, sort_method in pattern_order_loop:
                        
                        labels_and_values = []
                        for item in self.keys[i_key]:
                            for pattern, scaling in patterns_scalings:
                                item_match = re.match(pattern, item)
                                if item_match:
                                    # add the label and value to the list:
                                    if devmode:
                                        try:
                                            _ = float(item_match.group(1)) * scaling
                                        except:
                                            pdb.set_trace()
                                            print 'unable to convert item "%s" with pattern "%s" to float' % (item, pattern)
                                    labels_and_values.append( (item, float(item_match.group(1)) * scaling ) )
                                    break
                        # now sort the labels_and_values, according to the value:
                        if sort_method == 'sort':
                            labels_and_values.sort(key=lambda x: x[1])
                        elif sort_method == 'reversed':
                            labels_and_values.sort(key=lambda x: x[1], reverse=True)
                        else:
                            raise ValueError('Unrecognised sort_method "%s"' % sort_method)
                        # add the labels to the tmp_keys and remove them from the self.keys[i_key]:
                        for item, scaling in labels_and_values:
                            tmp_keys.append(item)
                            self.keys[i_key].pop( self.keys[i_key].index(item) )
                    
                    
                    # now sort what's left:
                    self.keys[i_key].sort()
                    
                    # and put the tmp_keys at the start of it:
                    self.keys[i_key] = tmp_keys + self.keys[i_key]
                    
            
            elif isinstance(method, list):
                # the input list should be a list of strings, which give the priority contents to be put at the start of the list.
                # The remaining items are sorted normally:
                # - specific model names get to the top, the rest are alphaebetical
                
                # add to tmp_keys as we go, by popping elements from the main list:
                tmp_keys = []
                # this sets the order of the model names (names not in this list are alphabetical):
                for item in method:
                    if item in self.keys[i_key]:
                        tmp_keys.append(self.keys[i_key].pop( self.keys[i_key].index(item) ))
                    if len(self.keys[i_key]) == 0:
                        break
                # now sort the remaining keys alphabetically:
                self.keys[i_key].sort()
                # and put the tmp_keys back in at the start:
                self.keys[i_key] = tmp_keys + self.keys[i_key]
 


def readmeta_from_image(img_file, img_format=None):
    'Reads the metadata added by the ImageMetaTag savefig, from an image file'

    if img_format is None:
        # get the img_format from the end of the filename
        _, img_format = os.path.splitext(img_file)
        if img_format is None or img_format == '':
            raise ValueError('Cannot determine file img_format to read from filename "%s"' % img_file)
        # get rid of the . to be consistent throughout
        img_format = img_format[1:]
    else:
        if img_format.startswith('.'):
            img_format = img_format[1:]

    # how we read in the metadata depends on the format:
    if img_format == 'png':
        try:
            img_obj = Image.open(img_file)
            img_info = img_obj.info
            read_ok = True
        except:
            # if anthing goes wrong, then read_ok is False and img_info None
            read_ok = False
            img_info = None
    else:
        raise NotImplementedError('Currently, ImageMetaTag does not support "%s" format images' % img_format)
    
    return (read_ok, img_info)

def dict_heirachy_from_list(in_dict, payload, heirachy):
    '''converts a flat dictionary, into an ordered dictionary of dictionaries according to the input heirachy (which is a list
    of metadata keys).
    The output dictionary will only have one element per level, but can be used to create or append into a ImageDict class above.
    The final level will be the 'payload' input, which is the object the dictionary, with all it's levels, is describing.
    The payload would usually be the full/relative path of the image file, or list of image files.
    
    Returns False if the input dict does not contain the required keys.
    '''
    for level in heirachy:
        if not level in in_dict.keys():
            return False
    
    out_dict = {in_dict[heirachy[-1]]: payload}  
    for level in heirachy[-2::-1]:
        out_dict = {in_dict[level]: out_dict}
    return out_dict


def dict_split(in_dict, n_split=None, size_split=None, extra_opts=None):
    '''Generator that breaks up a dictionary and yields a set of sub-dictionaries in 
      n_split chunks, or size_split in size.
    It is very useful for splitting large dictionaries of image metadata 
    to parallelise processing these into ImageDicts.
    
    Inputs:
    in_dict - the dictionary to split
    
    Options:
    n_split - the number of dictionaries to break the in_dict up into.
    
    size_split - the size of the required output dictionaries. 
     (One, and only one, of n_slpit, or size_split must be specified, as an integer.)
    
    extra_opts - If supplied as an iterable, this routine will yield a tuple containing the output
      sub-dictionary and then each of the elements of extra_opts.
     
    '''
    
    if not isinstance(in_dict, dict):
        raise ValueError('Input in_dict is not a dictionary')
    
    if len(in_dict) == 0:
        # an empty dict needs to output an empty dict, possiblty with the 
        # extra options:
        out_dict = {}
        if extra_opts is None:
            yield out_dict
        else:
            # yield a tuple containing the output dictionary, plus all the extra options, 
            # as elements in a tuple:
            out_tuple = (out_dict, )
            for opt in extra_opts:
                out_tuple = out_tuple + (opt,)
            yield out_tuple
    else:
        if size_split is None and isinstance(n_split, int):
            if n_split < 1:
                raise ValueError('Cannot split a dictionary into less than 1 dictionary')
            # work out the size of a split - the last dict can be smaller than the others:
            size_split = int( ceil( len(in_dict) / float(n_split)) )
        elif isinstance(size_split, int) and n_split is None:
            # do nothing, use the input size_split
            pass
        else:
            msg = 'One, and only one, of n_slpit, or size_split must be specified, as an integer.'
            raise ValueError(msg)
        
        iterdict = iter(in_dict)
        for i in xrange(0, len(in_dict), size_split):
            
            out_dict = {k:in_dict[k] for k in islice(iterdict, size_split)}
            
            if extra_opts is None:
                yield out_dict
            else:
                # yield a tuple containing the output dictionary, plus all the extra options, 
                # as elements in a tuple:
                out_tuple = (out_dict, )
                for opt in extra_opts:
                    out_tuple = out_tuple + (opt,)
                    
                yield out_tuple


