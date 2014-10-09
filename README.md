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
virtualenv --distribute venv
source ./venv/bin/activate
pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download
sudo apt-get install libxml2-dev libxslt-dev
pip install -r requirements.txt
````

````
cp nicobbs.config.sample nicobbs.config
vi nicobbs.config
cp nicobbs.env.sample nicobbs.env
vi nicobbs.env
````

configure mongo
--
run the following script to create indexes that are needed for proper query execution plan.

````
mongo your_database_name ./database/credb.js
````

kick
--
just use start, and stop.
````
./nicobbs.sh start
./nicobss.sh stop
````

monitoring example using crontab
--
see `nicobbs.sh` inside for the details of monitoring.

	# monitoring nicoalert
	* * * * * /path/to/nicobbs/nicobbs.sh monitor >> /path/to/nicobbs/log/monitor.log 2>&1

memo
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

launch mongodb installed through `brew install mongo`.
````
To have launchd start mongodb at login:
    ln -sfv /usr/local/opt/mongodb/*.plist ~/Library/LaunchAgents
Then to load mongodb now:
    launchctl load ~/Library/LaunchAgents/homebrew.mxcl.mongodb.plist
Or, if you don't want/need launchctl, you can just run:
    mongod --config /usr/local/etc/mongod.conf
````

license
--
copyright &copy; 2012- honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
