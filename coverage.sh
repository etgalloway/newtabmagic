# Script for generating a test coverage report
# Usage:
#   $ ./coverage.sh
coverage erase
tox
coverage html
