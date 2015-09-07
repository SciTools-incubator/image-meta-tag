'''
A python module providing a system of tagging image files as created by 
matplotlib and a web page and javascript image display interface based on tagged images.

@author: Malcolm.E.Brooks@metoffice.gov.uk
'''

from savefig import savefig, image_file_postproc
from img_dict import ImageDict
from img_dict import readmeta_from_image, dict_heirachy_from_list, dict_split
# we want all of the fucntions in webpage, as a separate level
import webpage