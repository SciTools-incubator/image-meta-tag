import os
import os.path
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
packages = []
for d, _, _ in os.walk(os.path.join(here, 'ImageMetaTag')):
    if os.path.exists(os.path.join(d, '__init__.py')):
        packages.append(d[len(here)+1:].replace(os.path.sep, '.'))

print packages
setup_args = dict(
    name='ImageMetaTag',
    version='0.2',
    description='Image metadata tagging, database and presentation',
    license='BSD3',
    author='Malcolm Brooks',
    url='https://github.com/SciTools-incubator/image-meta-tag',
    packages=packages,
    test_suite='python test.py',
    classifiers      = [
        'Programming Language :: Python :: 2.7',
    ],
)

if __name__ == '__main__':
    setup(**setup_args)
