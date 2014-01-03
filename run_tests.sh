#!/usr/bin/env bash

set -e
# set -x

env_files="./nicobbs.env ./tests/test.env"

for env_file in ${env_files}
do
  if [ -e ${env_file} ]; then
    source ${env_file}
  fi
done

# py.test tests
py.test --pep8 --cov nicobbs.py --cov nicoutil.py tests
