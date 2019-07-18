from setuptools import setup

setup(
    name="coach-cli",
    version='0.1',
    py_modules=['main'],
    install_requires=[
        'Click',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        coach=main:cli
    ''',
)