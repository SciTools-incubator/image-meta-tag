'''
This module contains a set of functions to create/write to/read
and maintain an sqlite3 database of image files and their associated metadata.

In normal usage it is primarily used by  :func:`ImageMetaTag.savefig` to create the database
as figures are saved. Once the metadata database has been built up then the metadata can be
loaded with :func:`ImageMetaTag.db.read`.

(C) Crown copyright Met Office. All rights reserved.
Released under BSD 3-Clause License. See LICENSE for more details.
'''

import os, sqlite3, fnmatch, time, errno, pdb

from ImageMetaTag import META_IMG_FORMATS, DEFAULT_DB_TIMEOUT, DEFAULT_DB_ATTEMPTS
from ImageMetaTag.img_dict import readmeta_from_image, check_for_required_keys

from datetime import datetime
import numpy as np
from cStringIO import StringIO

# the name of the database table that holds the sqlite database of plot metadata
SQLITE_IMG_INFO_TABLE = 'img_info'

def info_key_to_db_name(in_str):
    'Consistently convert a name in the img_info dict to something to be used in the database'
    return in_str.replace(' ', '__')

def db_name_to_info_key(in_str):
    'Inverse of info_key_to_db_name'
    # convert to string, to remove unicode string
    return str(in_str).replace('__', ' ')

def write_img_to_dbfile(db_file, img_filename, img_info, add_strict=False,
                        attempt_replace=False,
                        timeout=DEFAULT_DB_TIMEOUT):
    '''
    Writes image metadata to a database.

    Arguments:

    * db_file - the database file to write to. If it does not exist, it will be created.
    * img_filename - the filename of the image to which the metadata applies. Usually \
                     this is either the absolute path, or it is useful to make this \
                     the relative path, from the location of the database file.
    * img_info - a dictionary containing any number of  {tag_name: value}  pairs to be \
                 stored.

    Options:

    * add_strict - passed into :func:`ImageMetaTag.db.write_img_to_open_db`
    * attempt_replace - passed into :func:`ImageMetaTag.db.write_img_to_open_db`
    * timeout - default timeout to try and write to the database.

    This is commonly used in :func:`ImageMetaTag.savefig`
    '''

    if len(img_info) == 0:
        raise ValueError('Size of image info dict is zero')
    if db_file is None:
        pass
    else:
        # open the database:
        dbcn, dbcr = open_or_create_db_file(db_file, img_info, timeout=timeout)
        # now write:
        write_img_to_open_db(dbcr, img_filename, img_info,
                             add_strict=add_strict, attempt_replace=attempt_replace)
        # now commit that databasde entry and close:
        dbcn.commit()
        dbcn.close()

def read(db_file, required_tags=None, tag_strings=None,
         db_timeout=DEFAULT_DB_TIMEOUT,
         db_attempts=DEFAULT_DB_ATTEMPTS):
    '''
    reads in the database written by write_img_to_dbfile

    Options:
     * required_tags - a list of image tags to return, and to fail if not all are \
                       present
     * tag_strings - an input list that will be populated with the unique values of \
                     the image tags.

    Returns:
     * a list of filenames (payloads for the :class:`ImageMetaTag.ImageDict` class )
     * a dictionary, by filename, containing a dictionary of the image metadata \
       as *tagname: value*

    If tag_strings is not supplied, then the returned dictionary will contain a
    large number of duplicated strings, which can be an inefficient use of memory
    with large databases. If tag_strings is supplied, it will be populated with a
    unique list of strings used as tags and the dictionary will only contain
    references to this list. This can reduce memory usage considerably, both for
    the dictionary itself but also of an :class:`ImageMetaTag.ImageDict` produced
    with the dictionary.

    Will return None, None if there is a problem.

    In older versions, this was named read_img_info_from_dbfile which will still work.
    '''
    if db_file is None:
        return None, None
    else:
        if not os.path.isfile(db_file):
            return None, None
        else:
            n_tries = 1
            read_db = False
            while not read_db and n_tries <= db_attempts:
                try:
                    # open the connection and the cursor:
                    dbcn, dbcr = open_db_file(db_file, timeout=db_timeout)
                    # read it:
                    f_list, out_dict = read_img_info_from_dbcursor(dbcr,
                                                                   required_tags=required_tags,
                                                                   tag_strings=tag_strings)
                    # close connection:
                    dbcn.close()
                    read_db = True
                except sqlite3.OperationalError as op_err:
                    if 'database is locked' in op_err.message:
                        # database being locked is what the retries and timeouts are for:
                        print '%s database timeout reading from file "%s", %s s' \
                                % (dt_now_str(), db_file, n_tries * db_timeout)
                        n_tries += 1
                    elif op_err.message == 'no such table: {}'.format(SQLITE_IMG_INFO_TABLE):
                        # the db file exists, but it doesn't have anything in it:
                        return None, None
                    else:
                        # everything else needs to be reported and raised immediately:
                        msg = '{} for file {}'.format(op_err.message, db_file)
                        raise sqlite3.OperationalError(msg)

            # if we went through all the attempts then it is time to raise the error:
            if n_tries > db_attempts:
                msg = '{} for file {}'.format(op_err.message, db_file)
                raise sqlite3.OperationalError(msg)

            # close connection:
            dbcn.close()
            return f_list, out_dict

read_img_info_from_dbfile = read

def merge_db_files(main_db_file, add_db_file, delete_add_db=False,
                   delete_added_entries=False, attempt_replace=False,
                   db_timeout=DEFAULT_DB_TIMEOUT, db_attempts=DEFAULT_DB_ATTEMPTS):
    '''
    Merges two ImageMetaTag database files, with the contents of add_db_file added
    to the main_db_file. The databases should have the same tags within them for the
    merge to work.

    Options:

    * delete_add_db - if True, the added database file will be deleted afterwards
    * delete_added_entries - if delete_add_db is False, this will keep the add_db_file \
                             but remove the entries from it which were added to the \
                             main_db_file. \
                             This is useful if parallel processes are writing to the \
                             databases.  It does nothing if delete_add_db is True.
    '''

    # read what we want to add in:
    add_filelist, add_tags = read(add_db_file, db_timeout=db_timeout, db_attempts=db_attempts)
    if add_filelist is not None:
        if len(add_filelist) > 0:
            n_tries = 1
            wrote_db = False
            while not wrote_db and n_tries <= db_attempts:
                try:
                    # open the main database
                    dbcn, dbcr = open_db_file(main_db_file, timeout=db_timeout)
                    # and add in the new contents:
                    for add_file, add_info in add_tags.iteritems():
                        write_img_to_open_db(dbcr, add_file, add_info,
                                             attempt_replace=attempt_replace)
                    dbcn.commit()
                    # if we got here, then we're good!
                    wrote_db = True
                    # finally close:
                    dbcn.close()
                except sqlite3.OperationalError as op_err:
                    if 'database is locked' in op_err.message:
                        # database being locked is what the retries and timeouts are for:
                        print '%s database timeout writing to file "%s", %s s' \
                                        % (dt_now_str(), main_db_file, n_tries * db_timeout)
                        n_tries += 1
                    else:
                        # everything else needs to be reported and raised immediately:
                        msg = '{} for file {}'.format(op_err.message, main_db_file)
                        raise sqlite3.OperationalError(msg)

            # if we went through all the attempts then it is time to raise the error:
            if n_tries > db_attempts:
                msg = '{} for file {}'.format(op_err.message, main_db_file)
                raise sqlite3.OperationalError(msg)

    # delete or tidy:
    if delete_add_db:
        rmfile(add_db_file)
    elif delete_added_entries:
        del_plots_from_dbfile(add_db_file, add_filelist, do_vacuum=False,
                              allow_retries=True, skip_warning=True)

def open_or_create_db_file(db_file, img_info, restart_db=False, timeout=DEFAULT_DB_TIMEOUT):
    '''
    Opens a database file and sets up initial tables, then returns the connection and cursor.

    Arguments:
     * db_file - the database file to open.
     * img_info - a dictionary of image metadata to be saved to the database.

    Options:
     * restart_db - when Truem this deletes the current db file and starts again, \
                   if it already exists.

    Returns an open database connection (dbcn) and cursor (dbcr)
    '''

    if not os.path.isfile(db_file) or restart_db:
        if os.path.isfile(db_file):
            os.remove(db_file)
        # create a new database file:
        dbcn = sqlite3.connect(db_file)
        dbcr = dbcn.cursor()
        # and create the table:
        create_table_for_img_info(dbcr, img_info)
    else:
        # open the database file:
        dbcn, dbcr = open_db_file(db_file, timeout=timeout)
        # check for the required table:
        table_names = list_tables(dbcr)
        if SQLITE_IMG_INFO_TABLE not in table_names:
            # create it if required:
            create_table_for_img_info(dbcr, img_info)
    return dbcn, dbcr

def create_table_for_img_info(dbcr, img_info):
    'Creates a database table, in a database cursor, to store for the input img_info'

    create_command = 'CREATE TABLE {}(fname TEXT PRIMARY KEY,'.format(SQLITE_IMG_INFO_TABLE)
    for key in img_info.keys():
        create_command += ' "{}" TEXT,'.format(info_key_to_db_name(key))
    create_command = create_command[0:-1] + ')'
    # Can make a rare race condition if multiple processes try to create the file at the same time;
    # If that happens, the error is:
    # sqlite3.OperationalError: table img_info already exists for file .......
    try:
        dbcr.execute(create_command)
    except sqlite3.OperationalError as op_err:
        if 'table {} already exists'.format(SQLITE_IMG_INFO_TABLE) in op_err.message:
            # another process has just created the table, so sleep(1)
            # This is only when a db file is created so isn't called often
            # (and the race condition is rare!)
            time.sleep(1)
        else:
            # everything else needs to be reported and raised immediately:
            raise sqlite3.OperationalError(op_err.message)
    except sqlite3.Error as sq_err:
        # everything else needs to be reported and raised immediately:
        raise sqlite3.Error(sq_err.message)


def open_db_file(db_file, timeout=DEFAULT_DB_TIMEOUT):
    '''
    Just opens an existing db_file, using timeouts but no retries.

    Returns an open database connection (dbcn) and cursor (dbcr)
    '''

    dbcn = sqlite3.connect(db_file, timeout=timeout)
    dbcr = dbcn.cursor()

    return dbcn, dbcr

def read_db_file_to_mem(db_file, timeout=DEFAULT_DB_TIMEOUT):
    '''
    Opens a pre-existing database file into a copy held in memory. This can be accessed much
    faster when doing extenstive work (a lot of select operations, for instance).

    There is a time cost in doing this; it takes a few seconds to read in a large database,
    so it is only worth doing when doing a lot of operations.

    Tests on selects on a large-ish database (250k rows) suggested it was worth doing
    for > 100 selects.

    Returns an open database connection (dbcn) and cursor (dbcr)
    '''

    # read the database into an in-memory file object:
    #dbcn = sqlite3.connect(db_file)
    dbcn, _ = open_db_file(db_file, timeout=timeout)
    memfile = StringIO()
    for line in dbcn.iterdump():
        memfile.write('%s\n' % line)
    dbcn.close()
    memfile.seek(0)

    # Create a database in memory and import from memfile
    dbcn = sqlite3.connect(":memory:")
    dbcn.cursor().executescript(memfile.read())
    dbcn.commit()
    dbcr = dbcn.cursor()

    return dbcn, dbcr

def write_img_to_open_db(dbcr, filename, img_info, add_strict=False, attempt_replace=False):
    '''
    Does the work for write_img_to_dbfile to add an image to the open database cursor (dbcr)

    * add_strict: if True then it will report a ValueError if you \
                  try and include fields that aren't defined in the table
    * attempt_replace: if True, then it will attempt to replace a database \
                  entry if the image is already present. Otherwise it will ignore it.
    '''

    # now add in the information:
    # get the name of the fields from the cursor descripton:
    _ = dbcr.execute('select * from %s' % SQLITE_IMG_INFO_TABLE).fetchone()
    field_names = [r[0] for r in dbcr.description]
    # convert these to keys:
    field_names = [db_name_to_info_key(x) for x in field_names]
    # now build the command
    add_command = 'INSERT INTO {}(fname,'.format(SQLITE_IMG_INFO_TABLE)
    add_list = [filename]
    for key, item in img_info.iteritems():
        if key in field_names:
            add_command += ' "{}",'.format(info_key_to_db_name(key))
            add_list.append(item)
        elif add_strict:
            raise ValueError('Attempting to add a line to the database that include invalid fields')
    # add in the right number of ?
    add_command = add_command[0:-1] + ') VALUES(' + '?,'*(len(add_list)-1) + '?)'
    try:
        dbcr.execute(add_command, add_list)
    except sqlite3.IntegrityError:
        if attempt_replace:
            # try an INSERT OR REPLACE
            add_repl_command = add_command.replace('INSERT ', 'INSERT OR REPLACE ')
            # if this fails, want it to report it's error message as is, so no 'try':
            dbcr.execute(add_repl_command, add_list)
        else:
            # this file is already in the database (as the primary key, so do nothing...)
            pass
    finally:
        pass

def list_tables(dbcr):
    'lists the tables present, from a database cursor'
    result = dbcr.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    table_names = sorted(zip(*result)[0])
    return table_names

def read_img_info_from_dbcursor(dbcr, required_tags=None, tag_strings=None):
    '''
    Reads from an open database cursor (dbcr) for :func:`ImageMetaTag.db.read` and other routines.

    Options
     * required_tags - a list of image tags to return, and to fail if not all are present
     * tag_strings - an input list that will be populated with the unique values of the image tags
    '''
    # read in the data from the database:
    db_contents = dbcr.execute('select * from %s' % SQLITE_IMG_INFO_TABLE).fetchall()
    # and convert that to a useful dict/list combo:
    filename_list, out_dict = process_select_star_from(db_contents, dbcr,
                                                       required_tags=required_tags,
                                                       tag_strings=tag_strings)
    return filename_list, out_dict

def process_select_star_from(db_contents, dbcr, required_tags=None, tag_strings=None):
    '''
    Converts the output from a select * from ....  command into a standard output format
    Requires a database cursor (dbcr) to identify the field names.

    Options:
     * required_tags - a list of image tags to return, and to fail if not all are present
     * tag_strings - an input list that will be populated with the unique values of the image tags

    Returns:
     * as :func:`ImageMetaTag.db.read`, but filtered according to the select.
     * a list of filenames (payloads for the :class:`ImageMetaTag.ImageDict`)
     * a dictionary, by filename, containing a dictionary of the image metadata \
       as tagname: value
    '''
    # get the name of the fields from the cursor descripton:
    out_dict = {}
    filename_list = []
    # get the name of the fields from the cursor descripton:
    field_names = [r[0] for r in dbcr.description]

    # the required_tags input is a list of tag names (as strings):
    if required_tags is not None:
        if not isinstance(required_tags, list):
            raise ValueError('Input required_tags should be a list of strings')
        else:
            for test_str in required_tags:
                if not isinstance(test_str, str):
                    raise ValueError('Input required_tags should be a list of strings')

    if tag_strings is not None:
        if not isinstance(tag_strings, list):
            raise ValueError('Input tag_strings should be a list')

    # now iterate and make a dictionary to return,
    # with the tests outside the loops so they're not tested for every row and element:
    if required_tags is None and tag_strings is None:
        for row in db_contents:
            fname = str(row[0])
            filename_list.append(fname)
            img_info = {}
            for tag_name, tag_val in zip(field_names[1:], row[1:]):
                img_info[db_name_to_info_key(tag_name)] = str(tag_val)
            out_dict[fname] = img_info
            # return None, None if the contents are empty:
            if len(filename_list) == 0 and len(out_dict) == 0:
                return None, None
    elif required_tags is not None and tag_strings is None:
        for row in db_contents:
            fname = str(row[0])
            filename_list.append(fname)
            img_info = {}
            for tag_name, tag_val in zip(field_names[1:], row[1:]):
                tag_name_full = db_name_to_info_key(tag_name)
                if tag_name_full in required_tags:
                    img_info[tag_name_full] = str(tag_val)
            if len(img_info) != len(required_tags):
                raise ValueError('Database entry does not contain all of the required_tags')

            out_dict[fname] = img_info
            # return None, None if the contents are empty:
            if len(filename_list) == 0 and len(out_dict) == 0:
                return None, None
    elif required_tags is None and tag_strings is not None:
        # we want all tags, but we want them as referneces to a common list:
        for row in db_contents:
            fname = str(row[0])
            filename_list.append(fname)
            img_info = {}
            for tag_name, tag_val in zip(field_names[1:], row[1:]):
                str_tag_val = str(tag_val)
                try:
                    # loacate the tag_string in the list:
                    tag_index = tag_strings.index(str_tag_val)
                    # and refernece it:
                    img_info[db_name_to_info_key(tag_name)] = tag_strings[tag_index]
                except ValueError:
                    # tag not yet in the tag_strings list, so
                    # add the new string onto the end:
                    tag_strings.append(str_tag_val)
                    # and reference it:
                    img_info[db_name_to_info_key(tag_name)] = tag_strings[-1]
            out_dict[fname] = img_info
            # return None, None if the contents are empty:
            if len(filename_list) == 0 and len(out_dict) == 0:
                return None, None
    else:
        # we want to filter the tags, and we want them as referneces to a common list:
        for row in db_contents:
            fname = str(row[0])
            filename_list.append(fname)
            img_info = {}
            for tag_name, tag_val in zip(field_names[1:], row[1:]):
                # test to see if the tag name is required:
                tag_name_full = db_name_to_info_key(tag_name)
                if tag_name_full in required_tags:
                    str_tag_val = str(tag_val)
                    try:
                        # loacate the tag_string in the list:
                        tag_index = tag_strings.index(str_tag_val)
                        # and refernece it:
                        img_info[tag_name_full] = tag_strings[tag_index]
                    except ValueError:
                        # tag not yet in the tag_strings list, so
                        # add the new string onto the end:
                        tag_strings.append(str_tag_val)
                        # and reference it:
                        img_info[tag_name_full] = tag_strings[-1]
            out_dict[fname] = img_info
            # return None, None if the contents are empty:
            if len(filename_list) == 0 and len(out_dict) == 0:
                return None, None


    # we're good, return the data:
    return filename_list, out_dict

def del_plots_from_dbfile(db_file, filenames, do_vacuum=True, allow_retries=True,
                          db_timeout=DEFAULT_DB_TIMEOUT, db_attempts=DEFAULT_DB_ATTEMPTS,
                          skip_warning=False):
    '''
    deletes a list of files from a database file created by :mod:`ImageMetaTag.db`

    * do_vacuum - if True, the database will be restructured/cleaned after the delete
    * allow_retries - if True, retries will be allowed if the database is locked.\
                    If False there are no retries, but sleep commands try to avoid the need\
                    when doing a large number of deletes.
    * db_timeout - overide default database timeouts, if doing retries
    * db_attempts - overide default number of attempts, if doing retries
    * skip_warning - do not warn if a filename, that has been requested to be deleted,\
                   does not exist in the database
    '''
    if not isinstance(filenames, list):
        fn_list = [filenames]
    else:
        fn_list = filenames

    # delete command to use:
    del_cmd = "DELETE FROM {} WHERE fname=?"
    if db_file is None:
        pass
    else:
        if not os.path.isfile(db_file) or len(fn_list) == 0:
            pass
        else:
            if allow_retries:
                # split the list of filenames up into appropciately sized chunks, so that
                # concurrent delete commands each have a chance to complete:
                # 200 is arbriatily chosen, but seems to work
                chunk_size = 200
                chunks = __gen_chunk_of_list(fn_list, chunk_size)
                for chunk_o_filenames in chunks:
                    # within each chunk of files, need to open the db, with time out retries etc:
                    n_tries = 1
                    wrote_db = False
                    while not wrote_db and n_tries <= db_attempts:
                        try:
                            # open the database
                            dbcn, dbcr = open_db_file(db_file, timeout=db_timeout)
                            # go through the file chunk, one by one, and delete:
                            for fname in chunk_o_filenames:
                                try:
                                    dbcr.execute(del_cmd.format(SQLITE_IMG_INFO_TABLE), (fname,))
                                except sqlite3.OperationalError as op_err_file:
                                    err_check = 'no such table: {}'.format(SQLITE_IMG_INFO_TABLE)
                                    if op_err_file.message == err_check:
                                        # the db file exists, but it doesn't have anything in it:
                                        if not skip_warning:
                                            msg = ('WARNING: Unable to delete file entry "{}" from'
                                                   ' database "{}" as database table is missing')
                                            print msg.format(fname, db_file)
                                        return
                                    else:
                                        if not skip_warning:
                                            # if this fails, print a warning...
                                            # need to figure out why this happens
                                            msg = ('WARNING: unable to delete file entry:'
                                                   ' "{}", type "{}" from database')
                                            print msg.format(fname, type(fname))
                            dbcn.commit()
                            # if we got here, then we're good!
                            wrote_db = True
                            # finally close (for this chunk)
                            dbcn.close()
                        except sqlite3.OperationalError as op_err:
                            if 'database is locked' in op_err.message:
                                # database being locked is what the retries and timeouts are for:
                                print '%s database timeout deleting from file "%s", %s s' \
                                                % (dt_now_str(), db_file, n_tries * db_timeout)
                                n_tries += 1
                            elif 'disk I/O error' in op_err.message:
                                msg = '{} for file {}'.format(op_err.message, db_file)
                                raise IOError(msg)
                            else:
                                # everything else needs to be reported and raised immediately:
                                msg = '{} for file {}'.format(op_err.message, db_file)
                                raise ValueError(msg)

                    # if we went through all the attempts then it is time to raise the error:
                    if n_tries > db_attempts:
                        msg = '{} for file {}'.format(op_err.message, db_file)
                        raise sqlite3.OperationalError(msg)

            else:
                # just open the database:
                dbcn, dbcr = open_db_file(db_file)
                # delete the contents:
                for i_fn, fname in enumerate(fn_list):
                    try:
                        dbcr.execute(del_cmd.format(SQLITE_IMG_INFO_TABLE), (fname,))
                    except:
                        if not skip_warning:
                            # if this fails, print a warning...
                            # need to figure out why this happens
                            msg = ('WARNING: unable to delete file entry:'
                                   ' "{}", type "{}" from database')
                            print msg.format(fname, type(fname))
                    # commit every 100 to give other processes a chance:
                    if i_fn % 100 == 0:
                        dbcn.commit()
                        time.sleep(1)
                # commit, and vacuum if required:
                dbcn.commit()

            if do_vacuum:
                if allow_retries:
                    # need to re-open the db, if we allowed retries:
                    dbcn, dbcr = open_db_file(db_file)
                dbcn.execute("VACUUM")
                dbcn.close()
            elif not allow_retries:
                dbcn.close()

def __gen_chunk_of_list(in_list, chunk_size):
    'gnerator that yields a chunk of list, of length chunk size'
    for ndx in range(0, len(in_list), chunk_size):
        yield in_list[ndx:min(ndx + chunk_size, len(in_list))]

def select_dbfile_by_tags(db_file, select_tags):
    '''
    Selects from a database file the entries that match a dict of field names/acceptable values.

    Returns the output, processed by :func:`ImageMetaTag.db.process_select_star_from`
    '''
    if db_file is None:
        sel_results = None
    else:
        if not os.path.isfile(db_file):
            sel_results = None
        else:
            # just open the database:
            dbcn, dbcr = open_db_file(db_file)
            # do the select:
            sel_results = select_dbcr_by_tags(dbcr, select_tags)
            dbcn.close()
    return sel_results

def select_dbcr_by_tags(dbcr, select_tags):
    '''
    Selects from an open database cursor (dbcr) the entries that match a dict of field
    names & acceptable values.

    Returns the output, processed by :func:`ImageMetaTag.db.process_select_star_from`
    '''
    if len(select_tags) == 0:
        # just read and return the whole thing:
        return read_img_info_from_dbcursor(dbcr)
    else:
        # convert these to lists:
        tag_names = select_tags.keys()
        tag_values = [select_tags[x] for x in tag_names]
        # Right... this is where I need to understand how to do a select!
        #select_command = 'SELECT * FROM %s WHERE symbol=?' % SQLITE_IMG_INFO_TABLE
        select_command = 'SELECT * FROM %s WHERE ' % SQLITE_IMG_INFO_TABLE
        n_tags = len(tag_names)

        use_tag_values = []
        for i_tag, tag_name, tag_val in zip(range(n_tags), tag_names, tag_values):
            if isinstance(tag_val, (list, tuple)):
                # if a list or tuple, then use IN:
                select_command += '%s IN (' % info_key_to_db_name(tag_name)
                select_command += ', '.join(['?']*len(tag_val))
                select_command += ')'
                if i_tag+1 < n_tags:
                    select_command += ' AND '
                use_tag_values.extend(tag_val)
            else:
                # do an exact match:
                if i_tag+1 < n_tags:
                    select_command += '%s = ? AND ' % info_key_to_db_name(tag_name)
                else:
                    select_command += '%s = ?' % info_key_to_db_name(tag_name)
                use_tag_values.append(tag_val)
        db_contents = dbcr.execute(select_command, use_tag_values).fetchall()
        # and convert that to a useful dict/list combo:
        filename_list, out_dict = process_select_star_from(db_contents, dbcr)

    return filename_list, out_dict

def scan_dir_for_db(basedir, db_file, img_tag_req=None, subdir_excl_list=None,
                    known_file_tags=None, verbose=False, no_file_ext=False,
                    return_timings=False, restart_db=False):
    '''
    A useful utility that scans a directory on disk for images that can go into a database.
    This should only be used to build a database from a directory of tagged images that
    did not previously use a database, or where the database file has been deleted but the
    images have not.

    For optimal performance, build the database as the plots are created (or do not delete
    the database by accident).

    Arguments:
     * basedir - the directory to start scanning.
     * db_file - the database file to save the image metadata to. A pre-existing database file\
                will fail unless restart_db is True

    Options:
     * img_tag_req - a list of tag names that are to be applied/created. Tags not in this list\
                     will not be stored. Images without all of these tags are ignored.
     * subdir_excl_list - a list of subdirectories that don't need to be scanned. ['thumbnail']\
                         for instance, will prevent the image thumbnails being included.
     * no_file_ext - logical to exclude the file extension in the filenames saved to the database.
     * known_file_tags - if supplied, this is a dict (keyed by filename entry),\
                         contains a dictionary, structured: {filename: {tag name: value}} \
                         for the images that are already known (so you don't need to read them \
                         from the files themselves as that is slow). This can be useful \
                         if you have a old backup of a database file that needs updating.
     * restart_db - if True, the db_file will be restarted from an empty database.
     * verbose - verbose output.
    '''

    if os.path.isfile(db_file) and not restart_db:
        raise ValueError('''scan_dir_for_db will not work on a pre-existing file unless restart_db
is True, in which case the database file will be restarted as empty. Use with care.''')

    if known_file_tags is not None:
        known_files = known_file_tags.keys()
    else:
        known_files = []

    if return_timings:
        prev_time = datetime.now()
        add_interval = 1
        # total number of entries added
        n_added = 0
        # number of entries added since last timer
        n_add_this_timer = 0
        # and this is the list to return:
        n_adds = []
        timings_per_add = []

    os.chdir(basedir)
    first_img = True
    for root, dirs, files in os.walk('./', followlinks=True, topdown=True):
        if not subdir_excl_list is None:
            dirs[:] = [d for d in dirs if not d in subdir_excl_list]

        for meta_img_format in META_IMG_FORMATS:
            for filename in fnmatch.filter(files, '*%s' % meta_img_format):
                # append to the list, taking off the preceeding './' and the file extension:
                if root == './':
                    img_path = filename
                else:
                    img_path = '%s/%s' % (root[2:], filename)
                if no_file_ext:
                    img_name = os.path.splitext(img_path)[0]
                else:
                    img_name = img_path

                # read the metadata:
                if img_name in known_files:
                    # if we know this file details, then get it:
                    known_files.remove(img_name)
                    img_info = known_file_tags.pop(img_name)
                    read_ok = True
                else:
                    # otherwise read from disk:
                    (read_ok, img_info) = readmeta_from_image(img_path)

                if read_ok:
                    if img_tag_req:
                        # check to see if an image is needed:
                        use_img = check_for_required_keys(img_info, img_tag_req)
                    else:
                        use_img = True
                    if use_img:
                        if first_img:
                            db_cn, db_cr = open_or_create_db_file(db_file, img_info,
                                                                  restart_db=True)
                            first_img = False
                        write_img_to_open_db(db_cr, img_name, img_info)
                        if verbose:
                            print img_name

                        if return_timings:
                            n_added += 1
                            n_add_this_timer += 1
                            if n_add_this_timer % add_interval == 0:
                                time_interval_s = (datetime.now()- prev_time).total_seconds()
                                timings_per_add.append(time_interval_s / add_interval)
                                n_adds.append(n_added)
                                # increase the add_interval so we don't swamp
                                # the processing with timings!
                                add_interval = np.ceil(np.sqrt(n_added))
                                n_add_this_timer = 0
                                if verbose:
                                    print 'len(n_adds)=%s, currently every %s' \
                                            % (len(n_adds), add_interval)

    # commit and close, and we are done:
    if not first_img:
        db_cn.commit()
        db_cn.close()

    if return_timings:
        return n_adds, timings_per_add


def rmfile(path):
    """
    os.remove, but does not complain if the file has already been
    deleted (by a parallel process, for instance).
    """
    try:
        os.remove(path)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            pass
        else: raise

def dt_now_str():
    'returns datetime.now(), as a string, in a common format'
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
