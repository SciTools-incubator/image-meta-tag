ImageMetaTag is a python package built around a wrapper for savefig in matplotlib, which adds metadata tags to supported image file formats.

Once the images have been tagged, it can also be used to manage an SQL database of images and their metadata. The image metadata can be used to produce an ImageMetaTag.ImageDict object: a structured/heirachical dictionary of dictionaries which can be used to easily create web pages to present large numbers of images.

As the image metadata tagging process involves reading the image using the Image library, a few common image post-processing options are included such as cropping, logo addition and colour palette manipulation to reduce filesizes.

ImageMetaTag is released under a BSD 3-Clause License.

Supported image file formats: png
