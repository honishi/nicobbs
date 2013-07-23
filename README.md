nicoalert
=============

niconama bbs for twitter

how to use
-------------

1. virtualenv --distribute venv
2. source ./venv/bin/activate
3. pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download
4. sudo apt-get install libxml2-dev libxslt-dev
5. pip install -r requirements.txt

example crontab
-------------

	# monitoring nicoalert
	* * * * * /path/to/nicobbs/nicobbs.sh monitor >> /path/to/nicobbs/log/monitor.log 2>&1

license
-------------

copyright &copy; 2012- honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
