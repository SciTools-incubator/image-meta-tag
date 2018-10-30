.. ImageMetaTag documentation for bin

Associated scripts packaged with ImageMetaTag
=============================================

A small number of useful scripts are pacakged alongside the ImageMetaTag
library to interface with the library for common tasks.

rm_imt_images
-------------
Deletes images from disk and an ImageMetaTag database in a consistent way.

This script operates on a ImageMetaTag database file (imt.db in any examples).

Basic example:
::
 rm_imt_images imt.db file.png file2.png

this would delete file1.png and file2.png from disk and the imt.db file

Usage with wildcards:
::
 rm_imt_images.py /path/to/images/imt.db  /path/to/images/subdir/*

this would delete all files in the example subdirectory and their entry
in the database

Options:
 * -v : verbose output
 * -f : force deletes (similar to rm -f)

Note that this utility is not designed to delete files optimally for speed
but instead it deletes files on disk and then in the database one at a time.
This is slower than deleting multiple files on disk, and then multiple files
in the database, but this reduces the risk of the contents of the database
and file system getting out of sync.

Once a database file has been manipulated, and images deleted, any
web pages prepared using the database should be recreated. Doing so is
not part of this script.
