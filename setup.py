import setuptools
import sys

if sys.version_info <= (2, 7) or sys.version_info >= (3,7):
    sys.exit('coach-cli requires Python 3 -> Python 3.6')

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="coach-cli",
    version='0.8',
    py_modules=['main'],
    install_requires=[
        'Click',
        'boto3',
        'requests',
        'coach-ml==0.11',
    ],
    entry_points='''
        [console_scripts]
        coach=main:cli
    ''',
    author="Loren Kuich",
    author_email="loren@lkuich.com",
    description="CLI Utility for interacting with coach",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://coach.lkuich.com",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
