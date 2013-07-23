nicobbs to twitter
=============
![anokoku](https://dl.dropboxusercontent.com/u/444711/honishi.github.com/nicobbs/ankoku.jpeg)

scraping niconama bbs, and update status to twitter

sample
-------------
![tweets](https://dl.dropboxusercontent.com/u/444711/honishi.github.com/nicobbs/tweets.png)

requirements
-------------
1. python 2.6-
2. mongodb

how to setup
-------------
1. `git submodule update --init`
2. `virtualenv --distribute venv`
3. `source ./venv/bin/activate`
4. `pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download`
5. `sudo apt-get install libxml2-dev libxslt-dev`
6. `pip install -r requirements.txt`
7. `./nicobbs.sh start`, then `./nicobss.sh stop`

monitoring example using crontab
-------------
	# monitoring nicoalert
	* * * * * /path/to/nicobbs/nicobbs.sh monitor >> /path/to/nicobbs/log/monitor.log 2>&1

license
-------------
copyright &copy; 2012- honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
