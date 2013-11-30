#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
# import sys
import logging
import logging.config
import ConfigParser
import urllib2
import cookielib
import re
import time
import json

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
CRAWL_INTERVAL = 30
TWEET_INTERVAL = 3

# responses/lives just crawled from the web
STATUS_UNPROCESSED = "UNPROCESSED"
# spam responses
STATUS_SPAM = "SPAM"
# duplicate status updates
STATUS_DUPLICATE = "DUPLICATE"
# responses/lives that are failed to be posted to twitter. currently not used
STATUS_FAILED = "FAILED"
# reponses/lives that are successfully posted to twitter
STATUS_COMPLETED = "COMPLETED"

LOG_SEPARATOR = "---------- ---------- ---------- ---------- ----------"


class TwitterDuplicateStatusUpdateError(Exception):
    pass


class TwitterStatusUpdateError(Exception):
    pass


class NicoBBS(object):
# life cycle
    def __init__(self):
        logging.config.fileConfig(NICOBBS_CONFIG)
        self.logger = logging.getLogger("root")

        (self.mail, self.password, database_name, self.target_communities, self.ng_words) = (
            self.get_basic_config())
        self.logger.debug(
            "mail: %s password: xxxxxxxxxx database_name: %s "
            "target_communities: %s ng_words: %s" %
            (self.mail, database_name, self.target_communities, self.ng_words))

        self.consumer_key = {}
        self.consumer_secret = {}
        self.access_key = {}
        self.access_secret = {}
        for community in self.target_communities:
            (self.consumer_key[community], self.consumer_secret[community],
             self.access_key[community], self.access_secret[community]) = (
                self.get_community_config(community))
            self.logger.debug("*** community: " + community)
            self.logger.debug(
                "consumer_key: %s consumer_secret: xxxxxxxxxx" % self.consumer_key[community])
            self.logger.debug(
                "access_key: %s access_secret: xxxxxxxxxx" % self.access_key[community])

        self.connection = pymongo.Connection()
        self.database = self.connection[database_name]

    def __del__(self):
        self.connection.disconnect()

# utility
    def get_basic_config(self):
        config = ConfigParser.ConfigParser()
        config.read(NICOBBS_CONFIG)

        mail = config.get("nicobbs", "mail")
        password = config.get("nicobbs", "password")
        database_name = config.get("nicobbs", "database_name")
        target_communities = config.get("nicobbs", "target_communities").split(',')
        ng_words = config.get("nicobbs", "ng_words")
        if ng_words == '':
            ng_words = []
        else:
            ng_words = ng_words.split(',')

        return (mail, password, database_name, target_communities, ng_words)

    def get_community_config(self, community):
        config = ConfigParser.ConfigParser()
        config.read(NICOBBS_CONFIG)
        section = community

        consumer_key = config.get(section, "consumer_key")
        consumer_secret = config.get(section, "consumer_secret")
        access_key = config.get(section, "access_key")
        access_secret = config.get(section, "access_secret")

        return (consumer_key, consumer_secret, access_key, access_secret)

# twitter
    def update_twitter_status(self, community, status):
        auth = tweepy.OAuthHandler(self.consumer_key[community], self.consumer_secret[community])
        auth.set_access_token(self.access_key[community], self.access_secret[community])

        # for test; simulating post error like case of api limit
        # raise TwitterStatusUpdateError

        try:
            tweepy.API(auth).update_status(status)
        except tweepy.error.TweepError, error:
            self.logger.debug("twitter update error: %s" % error)
            # error.reason is the list object like following:
            #   [{"message":"Sorry, that page does not exist","code":34}]
            # see the following references for details:
            #   - https://dev.twitter.com/docs/error-codes-responses
            #   - ./tweepy/error.py

            # replace single quatation with double quatation to parse string properly
            normalized_reasons_string = re.sub("u'(.+?)'", r'"\1"', error.reason)

            reasons = json.loads(normalized_reasons_string)
            print reasons
            for reason in reasons:
                print reason
                if reason["code"] == 187:
                    # 'Status is a duplicate'
                    raise TwitterDuplicateStatusUpdateError
            raise TwitterStatusUpdateError

# nico nico
    def create_opener(self):
        # cookie
        cookiejar = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
        # self.logger.debug("finished setting up cookie library")

        # login
        opener.open(
            LOGIN_URL, "mail=%s&password=%s" % (self.mail, self.password))
        self.logger.debug("finished login")

        return opener

# bbs
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

    def get_bbs_responses(self, opener, url, community):
        # self.logger.debug(url)
        reader = opener.open(url)
        rawhtml = reader.read()
        self.logger.debug("finished to get raw responses.")
        # self.logger.debug(rawhtml)

        soup = BeautifulSoup(rawhtml)
        resheads = soup.findAll("dt", {"class": "reshead"})
        resbodies = soup.findAll("dd", {"class": "resbody"})
        responses = []
        index = 0
        for reshead in resheads:
            # extract
            number = reshead.find("a", {"class": "resnumhead"})["name"]
            name = reshead.find("span", {"class": "name"}).text.strip()
            # use "search", instead of "mathch". http://www.python.jp/doc/2.6/library/re.html#vs
            date = "n/a"
            se = re.search(DATE_REGEXP, reshead.text.strip())
            if se:
                date = se.group(1)
            hash_id = re.search(RESID_REGEXP, reshead.text.strip()).group(1)
            body = "".join([unicode(x) for x in resbodies[index]]).strip()
            body = self.sanitize_message(body)
            # self.logger.debug(u"[%s] [%s] [%s] [\n%s\n]".encode('utf_8') %
            # (number, name, date, body))
            index += 1

            # append
            response = {
                "community": community,
                "number": number,
                "name": name,
                "date": date,
                "hash": hash_id,
                "body": body,
                "status": STATUS_UNPROCESSED
            }
            responses.append(response)

        return responses

# message utility
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
                    messages.append(
                        name + u"[続き] " + bodies[counter] + u" [続く]")
                else:
                    messages.append(name + u"[続き] " + bodies[counter])
                counter += 1
        return messages

# reserved live
    def get_community_reserved_live(self, opener, community):
        url = COMMUNITY_TOP_URL + community
        self.logger.debug("scraping target: " + url)
        reader = opener.open(url)
        rawhtml = reader.read()
        self.logger.debug("finished to get raw community top page.")

        # self.logger.debug(rawhtml)
        # sys.exit()

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
                    reserved_live = {"community": community,
                                     "link": link,
                                     "community_name": community_name,
                                     "date": date.text,
                                     "title": anchor.text,
                                     "status": STATUS_UNPROCESSED}
                    reserved_lives.append(reserved_live)

        return reserved_lives

# mongo
    # response
# TODO: database index
    def register_response(self, response):
        self.database.response.update(
            {"community": response["community"], "number": response["number"]}, response, True)

    def is_response_registered(self, response):
        count = self.database.response.find(
            {"community": response["community"], "number": response["number"]}).count()
        return True if 0 < count else False

    def get_responses_with_community_and_status(self, community, status):
        responses = self.database.response.find(
            {"community": community, "status": status},
            sort=[("number", 1)])
        return responses

    def update_response_status(self, response, status):
        self.database.response.update(
            {"community": response["community"], "number": response["number"]},
            {"$set": {"status": status}})

    # reserved live
# TODO: database index
    def register_live(self, live):
        self.database.live.update(
            {"community": live["community"], "link": live["link"]}, live, True)

    def is_live_registered(self, live):
        count = self.database.live.find(
            {"community": live["community"], "link": live["link"]}).count()
        return True if 0 < count else False

    def get_lives_with_community_and_status(self, community, status):
        lives = self.database.live.find({"community": community, "status": status})
        return lives

    def update_live_status(self, live, status):
        self.database.live.update(
            {"community": live["community"], "link": live["link"]},
            {"$set": {"status": status}})

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
    # def page_number(self, strnum):
    #     intnum = int(strnum)
    #     return str(intnum - ((intnum-1) % 30))

    def crawl_bbs_response(self, opener, community):
        self.logger.debug("*** crawling responses, community: %s" % community)

        internal_url = self.get_bbs_internal_url(opener, community)
        responses = self.get_bbs_responses(opener, internal_url, community)
        self.logger.debug("scraped %s responses" % len(responses))
        for response in responses:
            if self.is_response_registered(response):
                self.logger.debug("already registered: #%s" % response["number"])
            else:
                self.register_response(response)
                self.logger.debug("registered: #%s" % response["number"])

        self.logger.debug("completed to crawl responses")

    def tweet_bbs_response(self, community):
        unprocessed_responses = self.get_responses_with_community_and_status(
            community, STATUS_UNPROCESSED)
        tweet_count = 0

        self.logger.debug("*** processing responses, community: %s unprocessed: %d" %
                          (community, unprocessed_responses.count()))

        for response in unprocessed_responses:
            self.logger.debug("processing response #%s" % response["number"])

            response_name = response["name"]
            response_body = response["body"]

            if (self.contains_ng_words(response_body) or
                    self.contains_too_many_link(response_body)):
                self.logger.debug(
                    "response contains ng word/too many video, so skip: [%s]" % response_body)
                self.update_response_status(response, STATUS_SPAM)
                continue

            # create message
            messages = self.create_message(response_name, response_body)
            for message in messages:
                if 0 < tweet_count:
                    self.logger.debug("sleeping %d secs before next tweet..." % TWEET_INTERVAL)
                    time.sleep(TWEET_INTERVAL)
                try:
                    self.update_twitter_status(community, message)
                except TwitterDuplicateStatusUpdateError, error:
                    # message is already posted to twitter. so response status should be
                    # changed from 'unprocessed' to other, in order to avoid reprocessing
                    self.logger.debug("twitter status update error, duplicate: %s" % error)
                    self.update_response_status(response, STATUS_DUPLICATE)
                    break
                except TwitterStatusUpdateError, error:
                    # twitter error case including api limit
                    # response status should not be changed here for future retrying
                    self.logger.debug("twitter status update error, unknown: %s" % error)
                    break
                else:
                    self.update_response_status(response, STATUS_COMPLETED)
                    self.logger.debug("status updated: [%s]" % message)
                    tweet_count += 1

        self.logger.debug("completed to process responses")

    def crawl_reserved_live(self, opener, community):
        self.logger.debug("*** crawling new reserved lives, community: %s" % community)
        reserved_lives = self.get_community_reserved_live(opener, community)
        self.logger.debug("scraped %s reserved lives" % len(reserved_lives))
        for reserved_live in reserved_lives:
            if self.is_live_registered(reserved_live):
                self.logger.debug("already registered: %s" % reserved_live["link"])
            else:
                self.register_live(reserved_live)
                self.logger.debug("registered: %s" % reserved_live["link"])

        self.logger.debug("completed to crawl reserved lives")

    def tweet_reserved_live(self, community):
        unprocessed_lives = self.get_lives_with_community_and_status(
            community, STATUS_UNPROCESSED)

        self.logger.debug("*** processing lives, community: %s unprocessed: %d" %
                          (community, unprocessed_lives.count()))

        for live in unprocessed_lives:
            self.logger.debug("processing live %s" % live["link"])

            message = (u"「" + live["community_name"] + u"」で生放送「" + live["title"] +
                       u"」が予約されました。" + live["date"] + u" " + live["link"])
            try:
                self.update_twitter_status(community, message)
            except TwitterDuplicateStatusUpdateError, error:
                self.logger.debug("twitter status update error, duplicate: %s", error)
                self.update_live_status(live, STATUS_DUPLICATE)
                break
            except TwitterStatusUpdateError, error:
                # twitter error case including api limit
                # response status should not be changed here for future retrying
                self.logger.debug("twitter status update error, unknown")
                break
            else:
                self.update_live_status(live, STATUS_COMPLETED)
                self.logger.debug("status updated: [%s]" % message)

        self.logger.debug("completed to process reserved lives")

    def start(self):
        # inifinite loop
        while True:
            try:
                self.logger.debug(LOG_SEPARATOR)
                opener = self.create_opener()
                for community in self.target_communities:
                    self.logger.debug(LOG_SEPARATOR)
                    try:
                        self.crawl_bbs_response(opener, community)
                        self.tweet_bbs_response(community)
                        self.crawl_reserved_live(opener, community)
                        self.tweet_reserved_live(community)
                    except Exception, error:
                        self.logger.debug("*** caught error: %s" % error)
            except Exception, error:
                self.logger.debug("*** caught error: %s" % error)

            self.logger.debug(LOG_SEPARATOR)
            self.logger.debug("*** sleeping %d secs..." % CRAWL_INTERVAL)
            time.sleep(CRAWL_INTERVAL)

if __name__ == "__main__":
    nicobbs = NicoBBS()
    nicobbs.start()
    # nicobbs.update_twitter_status("co1827022", "test")
