#!/usr/bin/env bash

basedir=$(cd $(dirname $0);pwd)
pyenv=${basedir}/venv/bin/activate
program=${basedir}/nicobbs.py
logfile=${basedir}/log/nicobbs.log
nohupfile=${basedir}/log/nohup.out
kill_python="python ${program}"
monitor_threshold=$((2*60))
dbname=$(grep database_name ${basedir}/nicobbs.config | cut -d'=' -f2 | tr -d ' ')
customenv=${basedir}/nicobbs.env

start() {
  nohup ${program} >> ${nohupfile} 2>&1 &
  return $?
}

stop() {
  pkill -f "${kill_python}"
  return $?
}

monitor() {
  echo $(date) monitor start

  last_modified=$(date -r ${logfile} +%s)
  # last_modified=0
  current=$(date +%s)
  # echo $last_modified
  # echo $current

  if [ $((${last_modified} + ${monitor_threshold})) -lt ${current} ]
  then
      echo $(date) "it seems that the file ${logfile} is not updated in ${monitor_threshold} seconds, so try to restart."
      stop
      start
  fi

  echo $(date) monitor end
}

oneshot() {
  ${program}
  return $?
}

clear() {
  mongo << _eof_
  use ${dbname}
  db.response.remove()
  db.gate.remove()
_eof_
}

find() {
  mongo << _eof_
  use ${dbname}
  db.response.find()
  db.gate.find()
_eof_
}

switch() {
  if [ $# -ne 1 ]; then
    echo "not enough arguments."
    echo "usage: ${0} switch dev|prod"
    return 1
  fi
    
  for target in nicobbs.config
  do
    rm ${target}
    ln -s ./${target}.${1} ./${target}
  done
  
  return 0
}

cd ${basedir}
source ${pyenv}

if [ -e ${customenv} ]; then
    source ${customenv}
fi

# env

case "$1" in
  start)
	stop
        start
        ;;
  stop)
        stop
        ;;
  restart)
        stop
        start
        ;;
  monitor)
        monitor
        ;;
  oneshot)
        oneshot
        ;;
  clear)
        clear
        ;;
  find)
        find
        ;;
  switch)
	shift
	switch $*
	;;
  *)
        echo $"Usage: $prog {start|stop|restart|monitor|oneshot|clear|find|switch}"
	exit 1
esac
