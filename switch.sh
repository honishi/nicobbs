#!/bin/bash

if [ $# -ne 1 ]; then
  echo "not enough arguments."
  echo "usage: ${0} dev|prod"
  exit 1
fi

for target in nicobbs.config twitter.config
do
rm ${target}
ln -s ./${target}.${1} ./${target}
done
