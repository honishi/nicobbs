nicoalert
=============

niconama bbs for twitter

how to use
-------------

1. virtualenv --distribute venv
2. source ./venv/bin/activate
4. pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download
3. pip install -r requirements.txt

example crontab
-------------

	# monitoring nicoalert
	* * * * * /home/honishi/nicobbs/nicobbs monitor >> /home/honishi/nicobbs/log/monitor.log 2>&1

license
-------------

copyright &copy; 2012 honishi, hiroyuki onishi.

distributed under the [MIT license][mit].
[mit]: http://www.opensource.org/licenses/mit-license.php
