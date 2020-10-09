import os
import setuptools


def read(fname):
    """Read the contents of a file present in the same dir as this py file"""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setuptools.setup(
    name="tw_frnds_ei",
    version="1.0.0",
    author="Marc Kirchner",
    author_email="kircmarc@gmail.com",
    description=("An export/import utility for downloading a Twitter user's friends (people whom they follow) "
                 "and creating those friendships in another Twitter user."),
    long_description=read('README'),
    packages=setuptools.find_packages(where='tw_frnds_ei'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Private :: Do not Upload",
    ],
    python_requires='>=3.8',
)
