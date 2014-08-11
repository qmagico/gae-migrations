python bootstrap
source bin/activate
pip install coverage

coverage erase
coverage run tests/testrunner.py
coverage xml

deactivate || : # virtualenv
