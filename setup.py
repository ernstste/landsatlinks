from codecs import open
from landsatlinks import __version__
from os.path import abspath, dirname, join
from setuptools import find_packages, setup
import sys


if sys.version_info < (3, 6):
    sys.exit('You need Python 3.6 or newer to install this package. Exiting.')

this_dir = abspath(dirname(__file__))
with open(join(this_dir, 'README.md'), encoding='utf-8') as file:
    long_description = file.read()


setup(
    name='landsatlinks',
    version=__version__,
    description='Generate and download Landsat Collection 2 Level 1 urls using the USGS/EROS machine-to-machine API.',
    long_description=long_description,
    url='https://github.com/ernstste/landsatlinks',
    author='Stefan Ernst',
    author_email='15325433+ernstste@users.noreply.github.com',
    license='MIT',
    keywords='landsat, usgs, m2m, api, download, earth observation, remote sensing',
    packages=find_packages(),
    install_requires=['requests', 'tqdm'],
    entry_points={
        'console_scripts': [
            'landsatlinks=landsatlinks.cli:main',
        ],
    },
)