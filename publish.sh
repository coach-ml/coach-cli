#!/bin/bash
rm -r build/ coach.egg-info/ dist/ lkuich.egg-info/
python3 setup.py sdist bdist_wheel

if [ $1 = "prod" ]; then
    python3 -m twine upload dist/*
else
    python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
fi