#!/usr/bin/env python
# -*- coding: utf-8 -*-

# use nicobbs
# db.response.ensureIndex({"communityId":1, "number":1})

import urllib2, cookielib, re, time, ConfigParser
import os
from bs4 import BeautifulSoup
import pymongo
import tweepy

# from os import path
import logging
import logging.config

# urls
LOGIN_URL = 'https://secure.nicovideo.jp/secure/login'
COMMUNITY_BBS_URL = 'http://com.nicovideo.jp/bbs/'
RESPONSE_URL = 'http://dic.nicovideo.jp/b/c/'
# VIDEO_ID_REGEXP = 'http://www.nicovideo.jp/watch/(.+)'
DATE_REGEXP = '.*(20../.+/.+\(.+\) .+:.+:.+).*'
RESID_REGEXP = 'ID: (.+)'

# const, directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGCONF_PATH = ROOT_DIR + '/log.conf'
NICOBBS_CONFIG = ROOT_DIR + '/' + 'nicobbs.config'

# const, crawl
CRAWL_INTERVAL = (1*60)
RETRY_INTERVAL = 10
TWEET_INTERVAL = 5

class NicoBBS(object):
# life cycle
    def __init__(self):
        # logging
        logging.config.fileConfig(NICOBBS_CONFIG)
        self.logger = logging.getLogger("root")
        # config
        self.dry_run, self.mail, self.password, self.database_name, self.target_community = self.get_config()
        # mongo
        self.conn = pymongo.Connection() 
        self.db = self.conn[self.database_name]
        # twitter
        self.twitter = self.get_twitter()

    def __del__(self):
        # mongo
        self.conn.disconnect()

# utility
    def get_config(self):
        config = ConfigParser.ConfigParser()
        config.read(NICOBBS_CONFIG)
        if config.get("nicobbs", "dry_run").lower() == "true":
            dry_run = True
        else:
            dry_run = False
        mail = config.get("nicobbs", "mail")
        password = config.get("nicobbs", "password")
        database_name = config.get("nicobbs", "database_name")
        target_community = config.get("nicobbs", "target_community")

        self.logger.debug("dry_run: %s mail: %s password: *** database_name: %s target_community: %s"
            % (dry_run, mail, database_name, target_community))

        return dry_run, mail, password, database_name, target_community

# twitter
    def get_twitter(self):
        config = ConfigParser.ConfigParser()
        config.read(NICOBBS_CONFIG)

        consumer_key = config.get("twitter", "consumer_key")
        consumer_secret = config.get("twitter", "consumer_secret")
        access_key = config.get("twitter", "access_key")
        access_secret = config.get("twitter", "access_secret")

        self.logger.debug("consumer_key: %s consumer_secret: *** access_key: %s access_secret: ***"
                % (consumer_key, access_key))

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_key, access_secret)

        return tweepy.API(auth)

    def update_status(self, status):
        try:
          self.twitter.update_status(status)
        except tweepy.error.TweepError, error:
          print u'error in post.'
          print error

    def remove_all(self):
        for status in tweepy.Cursor(self.twitter.user_timeline).items(1000):
            try:
                self.twitter.destroy_status(status.id)
            except tweepy.error.TweepError, error:
                print u'error in post destroy'
                print error
            sys.stdout.flush()

# nico nico
    def create_opener(self):
        # cookie
        cookiejar = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
        self.logger.debug("finished setting up cookie library.")

        # login
        opener.open(LOGIN_URL, "mail=%s&password=%s" % (self.mail, self.password))
        self.logger.debug("finished login.")

        return opener

    def get_bbs_internal_url(self, opener, community_id):
        # get bbs 
        url = COMMUNITY_BBS_URL + community_id
        # self.logger.debug(url)
        reader = opener.open(url)
        rawhtml = reader.read()
        self.logger.debug("finished to get raw bbs.")

        # print rawhtml
        # use regular expression, instead of beautifulsoup. because of html change.
        # soup = BeautifulSoup(rawhtml)
        # internal_url = soup.findAll("iframe")[0]['src']
        se = re.search('<iframe src="(.+?)"', rawhtml)
        internal_url = se.group(1)

        self.logger.debug("bbs internal url: " + internal_url)

        return internal_url

    def get_responses(self, opener, url, community_id):
        # get bbs 
        # self.logger.debug(url)
        reader = opener.open(url)
        rawhtml = reader.read()
        self.logger.debug("finished to get raw responses.")

        # print rawhtml
        # os.sys.exit()

        soup = BeautifulSoup(rawhtml)
        resheads = soup.findAll("dt", {"class": "reshead"})
        resbodies = soup.findAll("dd", {"class": "resbody"})
        responses = []
        index = 0
        for reshead in resheads:
            # extract
            number = reshead.find("a", {"class": "resnumhead"})["name"]
            name = reshead.find("span", {"class": "name"}).text.strip()
            # use "search", instead of "mathch"
            # http://www.python.jp/doc/2.6/library/re.html#vs
            date = "n/a"
            se = re.search(DATE_REGEXP, reshead.text.strip())
            if se: date = se.group(1)
            hash_id = re.search(RESID_REGEXP, reshead.text.strip()).group(1)
            body = "".join([unicode(x) for x in resbodies[index]]).strip()
            body = self.sanitize_message(body)
            # self.logger.debug(u"[%s] [%s] [%s] [\n%s\n]".encode('utf_8') % (number, name, date, body))
            index += 1

            # append
            response = {
                "communityId": community_id,
                "number": number,
                "name": name,
                "date": date,
                "hash": hash_id,
                "body": body
            }
            responses.append(response)

        return responses

# utility
    def sanitize_message(self, message):
        message = re.sub("<br/>", "\n", message)
        message = re.sub("<.*?>", "", message)
        message = re.sub("&gt;", ">", message)
        message = re.sub("&lt;", "<", message)

        return message
        
    def adjust_message(self, message):
        length = len(message)
        self.logger.debug("message length: %d" % length)
        adjusted = message
        # if length <= 119:
        if length <= 140:
            self.logger.debug("no need to adjust message.")
        else:
            # adjusted = message[0:119-3]
            adjusted = message[0:140-3]
            adjusted += "..."
        # self.logger.debug("adjusted: [%s]" % adjusted)

        return adjusted

# mongo
    # response
    def update_response(self, response):
        self.db.response.update({"communityId": response["communityId"], "number": response["number"]}, response, True)
        return

    def is_registered(self, response):
        count = self.db.response.find({"communityId": response["communityId"], "number": response["number"]}).count()
        return True if 0 < count else False

# main
    def page_number(self, strnum):
        intnum = int(strnum)
        return str(intnum - ((intnum-1) % 30))

    def crawl(self):
        self.logger.debug("started crawling.")

        tweet_count = 0
        opener = self.create_opener()
        internal_url = self.get_bbs_internal_url(opener, self.target_community)
        responses = self.get_responses(opener, internal_url, self.target_community)
        self.logger.debug("scraped %s responses", len(responses))
        for response in responses:
            if self.is_registered(response):
                pass
                # self.logger.debug("registered: [%s]" % response)
            else:
                # self.logger.debug("un-registered: [%s]" % response)
                if not self.dry_run:
                    self.update_response(response)
                # create message
                message = "(%s)\n%s" % (response["name"], response["body"])
                message = self.adjust_message(message)
                # num = response["number"]
                # message += " " + RESPONSE_URL + self.target_community + "/" + self.page_number(num) + "-#" + num
                # sleep before tweet
                if 0 < tweet_count:
                    self.logger.debug("will sleep %d secs before next tweet..." % TWEET_INTERVAL)
                    time.sleep(TWEET_INTERVAL)
                if not self.dry_run:
                    self.update_status(message)
                self.logger.debug("[" + message + "]")
                tweet_count += 1

        self.logger.debug("finished crawling.")
        return

    def go(self):
        # inifinite loop
        while True:
            try:
                # crawl
                self.logger.debug("**********")
                self.crawl()
                # sleep
                self.logger.debug("will sleep %d secs." % CRAWL_INTERVAL)
                time.sleep(CRAWL_INTERVAL)
            except Exception, error:
                self.logger.debug(error)
                self.logger.debug("caught error, will retry %s seconds later..." % RETRY_INTERVAL)
                time.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    nicobbs = NicoBBS()
    nicobbs.go()

