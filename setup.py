import setuptools
import sys

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="coach-cli",
    version='0.99',
    py_modules=['main'],
    install_requires=[
        'Click',
        'boto3',
        'requests',
        'coach-ml==0.16',
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
