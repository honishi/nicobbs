#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import logging.config
import ConfigParser
import urllib2
import cookielib
import re
import time

from bs4 import BeautifulSoup
import pymongo
import tweepy

LOGIN_URL = 'https://secure.nicovideo.jp/secure/login'
COMMUNITY_TOP_URL = 'http://com.nicovideo.jp/community/'
COMMUNITY_BBS_URL = 'http://com.nicovideo.jp/bbs/'
RESPONSE_URL = 'http://dic.nicovideo.jp/b/c/'
DATE_REGEXP = '.*(20../.+/.+\(.+\) .+:.+:.+).*'
RESID_REGEXP = 'ID: (.+)'
NICOBBS_CONFIG = os.path.dirname(os.path.abspath(__file__)) + '/nicobbs.config'
CRAWL_INTERVAL = (1*60)
RETRY_INTERVAL = 10
TWEET_INTERVAL = 5

class NicoBBS(object):
# life cycle
    def __init__(self):
        logging.config.fileConfig(NICOBBS_CONFIG)
        self.logger = logging.getLogger("root")
        (self.dry_run, self.mail, self.password, self.database_name,
            self.target_community, self.ng_words) = self.get_config()
        self.conn = pymongo.Connection() 
        self.db = self.conn[self.database_name]
        self.twitter = self.get_twitter()

    def __del__(self):
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
        ng_words = config.get("nicobbs", "ng_words")
        if ng_words == '':
            ng_words = []
        else:
            ng_words = ng_words.split(',')

        self.logger.debug("dry_run: %s mail: %s password: *** "
            "database_name: %s target_community: %s ng_words: %s" %
            (dry_run, mail, database_name, target_community, ng_words))

        return (dry_run, mail, password, database_name,
                target_community, ng_words)

# twitter
    def get_twitter(self):
        config = ConfigParser.ConfigParser()
        config.read(NICOBBS_CONFIG)

        consumer_key = config.get("twitter", "consumer_key")
        consumer_secret = config.get("twitter", "consumer_secret")
        access_key = config.get("twitter", "access_key")
        access_secret = config.get("twitter", "access_secret")

        self.logger.debug("consumer_key: %s consumer_secret: ***"
            "access_key: %s access_secret: ***" %
            (consumer_key, access_key))

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
            # sys.stdout.flush()

# nico nico
    def create_opener(self):
        # cookie
        cookiejar = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
        self.logger.debug("finished setting up cookie library.")

        # login
        opener.open(LOGIN_URL, "mail=%s&password=%s" %
            (self.mail, self.password))
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
        # use scraping by regular expression, instead of by beautifulsoup.
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
            # self.logger.debug(u"[%s] [%s] [%s] [\n%s\n]".encode('utf_8') %
            # (number, name, date, body))
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
        
    def split_body(self, body, split_length):
        location = 0
        bodies = []
        while location < len(body):
            bodies.append(body[location:location+split_length])
            location += split_length
        return bodies

    def create_message(self, name, body):
        name = "(%s)\n" % name
        length = len(name) + len(body)
        self.logger.debug("message length: %d" % length)
        messages = []
        if length <= 140:
            self.logger.debug("no need to split message body")
            messages.append(name + body)
        else:
            self.logger.debug("split message body")
            bodies = self.split_body(body, 140-len(name)-5*2)
            counter = 0
            while counter < len(bodies):
                if counter == 0:
                    messages.append(name + bodies[counter] + u" [続く]")
                elif counter < len(bodies)-1:
                    messages.append(name + u"[続き] " + bodies[counter]
                        + u" [続く]")
                else:
                    messages.append(name + u"[続き] " + bodies[counter])
                counter += 1
        return messages

# reserved live
    def get_reserved_live(self, opener, community_id):
        url = COMMUNITY_TOP_URL + community_id
        self.logger.debug("scraping target: " + url)
        reader = opener.open(url)
        rawhtml = reader.read()
        self.logger.debug("finished to get raw responses.")

        # print rawhtml
        # os.sys.exit()

        reserved_lives = []
        soup = BeautifulSoup(rawhtml)
        community_name = soup.find("h1", {"id": "community_name"}).text
        lives = soup.findAll("div", {"class": "item"})

        for live in lives:
            date = live.find("p", {"class": "date"})
            title = live.find("p", {"class": "title"})
            if title:
                anchor = title.find("a")
                link = anchor["href"]
                se = re.search("/gate/", link)
                if se:
                    date = date.text
                    title = anchor.text
                    message = (u"「" + community_name + u"」で生放送「" +
                        title + u"」が予約されました。" + date + u" " + link)
                    reserved_lives.append({"link":link, "message":message})

        return reserved_lives

# mongo
    # response
    def update_response(self, response):
        self.db.response.update({"communityId": response["communityId"],
            "number": response["number"]}, response, True)

    def is_response_registered(self, response):
        count = self.db.response.find({"communityId": response["communityId"],
            "number": response["number"]}).count()
        return True if 0 < count else False

    # reserved live (gate)
    def update_gate(self, link):
        self.db.gate.update({"link": link}, {"link": link}, True)

    def is_gate_registered(self, link):
        count = self.db.gate.find({"link": link}).count()
        return True if 0 < count else False

# filter
    def contains_ng_words(self, message):
        for word in self.ng_words:
            if re.search(word, message):
                return True
        return False

    def contains_too_many_link(self, message):
        videos = re.findall("sm\d{5,}", message)
        communities = re.findall("co\d{5,}", message)
        limit = 5
        if limit < len(videos) or limit < len(communities):
            return True
        return False

# main
    def page_number(self, strnum):
        intnum = int(strnum)
        return str(intnum - ((intnum-1) % 30))

    def crawl(self):
        self.logger.debug("started crawling.")

        tweet_count = 0
        opener = self.create_opener()

        internal_url = self.get_bbs_internal_url(opener, self.target_community)
        responses = self.get_responses(opener, internal_url,
            self.target_community)
        self.logger.debug("scraped %s responses", len(responses))
        for response in responses:
            resname = response["name"]
            resbody = response["body"]
            if (self.contains_ng_words(resbody) or
                self.contains_too_many_link(resbody)):
                self.logger.debug("contains ng word/too many video.")
                self.logger.debug("skipped: [" + resbody + "]")
                continue
            if self.is_response_registered(response):
                # self.logger.debug("registered: [%s]" % response)
                pass
            else:
                # self.logger.debug("un-registered: [%s]" % response)
                if not self.dry_run:
                    self.update_response(response)
                # create message
                messages = self.create_message(resname, resbody)
                for message in messages:
                    if 0 < tweet_count:
                        self.logger.debug("will sleep %d secs before next"
                            " tweet..." % TWEET_INTERVAL)
                        time.sleep(TWEET_INTERVAL)
                    if not self.dry_run:
                        self.update_status(message)
                    self.logger.debug("[" + message + "]")
                    tweet_count += 1

        self.logger.debug("checking new reserved live.")
        reserved_lives = self.get_reserved_live(opener, self.target_community)
        for reserved_live in reserved_lives:
            if self.is_gate_registered(reserved_live["link"]):
                pass
            else:
                self.update_gate(reserved_live["link"])
                self.update_status(reserved_live["message"])

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
                self.logger.debug(
                    "caught error, will retry %s seconds later..." %
                    RETRY_INTERVAL)
                time.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    nicobbs = NicoBBS()
    nicobbs.go()
