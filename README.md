nicobbs to twitter
==
![anokoku](https://dl.dropboxusercontent.com/u/444711/github.com/honishi/nicobbs/ankoku.jpeg)

scraping niconama bbs, and update status to twitter

sample
--
![tweets](https://dl.dropboxusercontent.com/u/444711/github.com/honishi/nicobbs/tweets.png)

requirements
--
1. python 2.6-
2. mongodb

setup
--
````
$ git submodule update --init
$ virtualenv --distribute venv
$ source ./venv/bin/activate
$ pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download
$ sudo apt-get install libxml2-dev libxslt-dev
$ pip install -r requirements.txt
````

tuning mongo
--
````
$ mongo
$ show dbs
$ use nicobbs
$ show collections

# response
$ db.response.find()
$ db.response.getIndexes()
$ db.response.ensureIndex({communityId:1, number:1})
$ db.response.getIndexes()

# gate
$ db.gate.find()
$ db.gate.getIndexes()
$ db.gate.ensureIndex({link:1})
$ db.gate.getIndexes()
````

kick
--
````
# start
$ ./nicobbs.sh start
# stop
$ ./nicobss.sh stop
````

monitoring example using crontab
--
	# monitoring nicoalert
	* * * * * /path/to/nicobbs/nicobbs.sh monitor >> /path/to/nicobbs/log/monitor.log 2>&1

license
--
copyright &copy; 2012- honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
