.. ImageMetaTag documentation for ImageMetaTag.db

ImageMetaTag.db
========================================

.. automodule:: ImageMetaTag.db

Commonly used functions
----------------------- 

For most use cases, the following functions provide the required functionality to use the database:

.. autofunction:: ImageMetaTag.db.write_img_to_dbfile
.. autofunction:: read_img_info_from_dbfile
.. autofunction:: ImageMetaTag.db.del_plots_from_dbfile
.. autofunction:: ImageMetaTag.db.select_dbfile_by_tags

Functions for opening/creating db files
---------------------------------------

.. autofunction:: ImageMetaTag.db.open_or_create_db_file
.. autofunction:: ImageMetaTag.db.open_db_file
.. autofunction:: ImageMetaTag.db.read_db_file_to_mem

Functions for working with open databases
-----------------------------------------

.. autofunction:: ImageMetaTag.db.write_img_to_open_db
.. autofunction:: ImageMetaTag.db.read_img_info_from_dbcursor
.. autofunction:: ImageMetaTag.db.select_dbcr_by_tags

Internal functions
------------------

.. autofunction:: ImageMetaTag.db.db_name_to_info_key
.. autofunction:: ImageMetaTag.db.info_key_to_db_name
.. autofunction:: ImageMetaTag.db.process_select_star_from

Utility functions
------------------
The following functions may be very useful for specific occasions, but are nopt intended for regular use:

.. autofunction:: ImageMetaTag.db.scan_dir_for_db

