import os
import os.path
from setuptools import setup
from glob import glob

# get the pako javascript library to the local version before we proceed:
# import the version of ImageMetaTag that's been downloaded:
try:
    import ImageMetaTag as imt
    # now get pako into that directory:
    imt.webpage.get_pako()
except:
    pass

here = os.path.abspath(os.path.dirname(__file__))
packages = []
for d, _, _ in os.walk(os.path.join(here, 'ImageMetaTag')):
    if os.path.exists(os.path.join(d, '__init__.py')):
        packages.append(d[len(here)+1:].replace(os.path.sep, '.'))

setup_args = dict(
    name = 'ImageMetaTag',
    version = '0.6.6',
    # for consistency, the version here should match:
    # ImageMetaTag/__init__.py
    # ImageMetaTag/javascript/imt_dropdown.js
    # docs/source/conf.py
    # setup.py
    description = 'Image metadata tagging, database and presentation',
    license = 'BSD3',
    author = 'Malcolm Brooks',
    url = 'https://github.com/SciTools-incubator/image-meta-tag',
    packages = packages,
    test_suite = 'python test.py',
    classifiers = ['Programming Language :: Python :: 2.7',
                  ],
    package_data = {'ImageMetaTag': ['javascript', 'javascript/*']},
)

if __name__ == '__main__':
    setup(**setup_args)
