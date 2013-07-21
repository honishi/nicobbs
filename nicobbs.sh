#!/usr/bin/env bash

basedir=$(cd $(dirname $0);pwd)
pyenv=${basedir}/venv/bin/activate
program=${basedir}/nicobbs.py
logfile=${basedir}/log/nicobbs.log
kill_python="python ${program}"
monitor_threshold=$((2*60))
dbname=$(grep database_name ${basedir}/nicobbs.config | cut -d'=' -f2 | tr -d ' ')

# these settings are needed for calling ffmpeg etc from python
export LANG=en_US.UTF-8
# export PATH=${PATH}:/usr/local/bin

start() {
    nohup ${program} >> ${logfile} 2>&1 &
    RETVAL=$?
    return $RETVAL
}

stop() {
    pkill -f "${kill_python}"
    RETVAL=$?
    return $RETVAL
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

clear() {
    mongo << _eof_
    use ${dbname}
    db.response.remove()
_eof_
}

find() {
    mongo << _eof_
    use ${dbname}
    db.response.find()
_eof_
}

source ${pyenv}

case "$1" in
  start)
        # start
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
  clear)
        clear
        ;;
  find)
        find
        ;;
  *)
        echo $"Usage: $prog {start|stop|restart|monitor|clear|find}"
        RETVAL=2
esac

exit $RETVAL

