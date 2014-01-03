nicobbs to twitter
==
[![Build Status](https://travis-ci.org/honishi/nicobbs.png?branch=develop)](https://travis-ci.org/honishi/nicobbs)
[![Coverage Status](https://coveralls.io/repos/honishi/nicobbs/badge.png?branch=develop)](https://coveralls.io/r/honishi/nicobbs?branch=develop)

scraping niconama bbs, and update status to twitter.

sample
--
![tweets](./sample/tweets.png)

requirements
--
1. python 2.7.x-
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

configure mongo
--
run the following script to create indexes that are needed for proper query execution plan.

````
$ mongo your_database_name ./credb.js
````

kick
--
just start, and stop.
````
$ ./nicobbs.sh start
$ ./nicobss.sh stop
````

monitoring example using crontab
--
see `nicobbs.sh` inside for the details of monitoring.

	# monitoring nicoalert
	* * * * * /path/to/nicobbs/nicobbs.sh monitor >> /path/to/nicobbs/log/monitor.log 2>&1

snippets for me
--
copy collections to another database.
````
use from_database_name
db.response.find().forEach(function(d){ db.getSiblingDB('to_database_name')['response'].insert(d); });
db.live.find().forEach(function(d){ db.getSiblingDB('to_database_name')['live'].insert(d); });
db.news.find().forEach(function(d){ db.getSiblingDB('to_database_name')['news'].insert(d); });
db.video.find().forEach(function(d){ db.getSiblingDB('to_database_name')['video'].insert(d); });
````
- http://stackoverflow.com/a/11554924

license
--
copyright &copy; 2012- honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
