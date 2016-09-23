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
import json

import nicoutil
from bs4 import BeautifulSoup
import pymongo
from slackclient import SlackClient
import tweepy

NICOBBS_CONFIG = os.path.dirname(os.path.abspath(__file__)) + '/nicobbs.config'
NICOBBS_CONFIG_SAMPLE = NICOBBS_CONFIG + '.sample'

LOGIN_URL = 'https://secure.nicovideo.jp/secure/login'
COMMUNITY_TOP_URL = 'http://com.nicovideo.jp/community/'
COMMUNITY_VIDEO_URL = 'http://com.nicovideo.jp/video/'
COMMUNITY_BBS_URL = 'http://com.nicovideo.jp/bbs/'
CHANNEL_BASE_URL = 'http://ch.nicovideo.jp/'

DATE_REGEXP = '.*(20../.+/.+\(.+\) .+:.+:.+).*'
RESID_REGEXP = 'ID: (.+)'

SKIP_LINK_REGEXPS = ["sm\d{5,}", "co\d{5,}", "lv\d{9,}", "ch\d{5,}", "im\d{5,}", "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"]
MAX_SKIP_LINKS_IN_RESPONSE = 5

DELETED_MESSAGE = u"削除しました"

CRAWL_INTERVAL = 30
COMMUNITY_INTERVAL = 10
TWEET_INTERVAL = 3

# responses/lives just crawled from the web
STATUS_UNPROCESSED = "UNPROCESSED"
# spam responses
STATUS_SPAM = "SPAM"
# duplicate status updates
STATUS_DUPLICATE = "DUPLICATE"
# over 140 characters
STATUS_OVER_CHARS = "OVER_CHARS"
# already deleted responses
STATUS_DELETED = "DELETED"
# responses/lives that are failed to be posted to twitter. currently not used
STATUS_FAILED = "FAILED"
# reponses/lives that are successfully posted to twitter
STATUS_COMPLETED = "COMPLETED"

LOG_SEPARATOR = "---------- ---------- ---------- ---------- ----------"


class TwitterStatusUpdateError(Exception):
# magic methods
    def __init__(self, message="", code=0):
        self.message = message
        self.code = code

    def __str__(self):
        return "status: [%s] code: [%d]" % (self.message, self.code)


class TwitterDuplicateStatusUpdateError(TwitterStatusUpdateError):
    pass


class TwitterOverCharactersStatusUpdateError(TwitterStatusUpdateError):
    pass


class TwitterSpamStatusUpdateError(TwitterStatusUpdateError):
    pass


class TwitterOverUpdateLimitError(TwitterStatusUpdateError):
    pass


class NicoBBS(object):
# life cycle
    def __init__(self):
        config_file = NICOBBS_CONFIG
        if not os.path.exists(config_file):
            config_file = NICOBBS_CONFIG_SAMPLE

        logging.config.fileConfig(config_file)
        logging.debug("initialized logger w/ file %s" % config_file)

        self.mail, self.password, database_name, self.ng_words, self.slack_token = (
            self.get_basic_config(config_file))
        logging.debug(
            "mail: %s password: xxxxxxxxxx database_name: %s ng_words: %s slack_token: %s" %
            (self.mail, database_name, self.ng_words, self.slack_token))

        self.target_communities = []
        self.consumer_key = {}
        self.consumer_secret = {}
        self.access_key = {}
        self.access_secret = {}
        self.skip_bbs = {}
        self.skip_live = {}
        self.skip_news = {}
        self.skip_video = {}
        self.response_number_prefix = {}
        self.mark_hashes = {}
        self.slack_id = {}

        for (community, consumer_key, consumer_secret, access_key, access_secret,
                skip_bbs, skip_live, skip_news, skip_video, response_number_prefix,
                mark_hashes, slack_id) in self.get_community_config(config_file):
            self.target_communities.append(community)
            self.consumer_key[community] = consumer_key
            self.consumer_secret[community] = consumer_secret
            self.access_key[community] = access_key
            self.access_secret[community] = access_secret
            self.skip_bbs[community] = skip_bbs
            self.skip_live[community] = skip_live
            self.skip_news[community] = skip_news
            self.skip_video[community] = skip_video
            self.response_number_prefix[community] = response_number_prefix
            self.mark_hashes[community] = mark_hashes
            self.slack_id[community] = slack_id

            logging.debug("*** community: " + community)
            logging.debug("consumer_key: %s secret: xxxxx" % self.consumer_key[community])
            logging.debug("access_key: %s secret: xxxxx" % self.access_key[community])
            logging.debug("skip_bbs: %d" % self.skip_bbs[community])
            logging.debug("skip_live: %d" % self.skip_live[community])
            logging.debug("skip_news: %d" % self.skip_news[community])
            logging.debug("skip_video: %d" % self.skip_video[community])
            logging.debug("response_number_prefix: " + self.response_number_prefix[community])
            logging.debug("mark_hashes: %s" % self.mark_hashes[community])
            logging.debug("slack_id: %s" % self.slack_id[community])

        self.connection = pymongo.Connection()
        self.database = self.connection[database_name]

    def __del__(self):
        self.connection.disconnect()

# utility
    def get_basic_config(self, config_file):
        defaults = {
            "slack_token": None}

        config = ConfigParser.ConfigParser(defaults)
        config.read(config_file)
        section = "nicobbs"

        mail = config.get(section, "mail")
        password = config.get(section, "password")
        database_name = config.get(section, "database_name")
        ng_words = unicode(config.get(section, "ng_words"), 'utf-8')
        if ng_words == '':
            ng_words = []
        else:
            ng_words = ng_words.split(',')
        slack_token = config.get(section, "slack_token")
        if slack_token == '':
            slack_token = None

        return mail, password, database_name, ng_words, slack_token

    def get_community_config(self, config_file):
        result = []

        defaults = {
            "skip_bbs": "false",
            "skip_live": "false",
            "skip_news": "false",
            "skip_video": "false",
            "response_number_prefix": "",
            "mark_hashes": None,
            "slack_id": None}

        config = ConfigParser.ConfigParser(defaults)
        config.read(config_file)

        for section in config.sections():
            matched = re.match(r'community-(.+)', section)
            if matched:
                community = matched.group(1)

                consumer_key = config.get(section, "consumer_key")
                consumer_secret = config.get(section, "consumer_secret")
                access_key = config.get(section, "access_key")
                access_secret = config.get(section, "access_secret")

                skip_bbs = config.getboolean(section, "skip_bbs")
                skip_live = config.getboolean(section, "skip_live")
                skip_news = config.getboolean(section, "skip_news")
                skip_video = config.getboolean(section, "skip_video")

                response_number_prefix = unicode(
                    config.get(section, "response_number_prefix"), 'utf-8')

                mark_hashes = config.get(section, "mark_hashes")
                if mark_hashes is None:
                    mark_hashes = []
                else:
                    mark_hashes = mark_hashes.split(',')

                slack_id = config.get(section, "slack_id")

                result.append((community, consumer_key, consumer_secret, access_key,
                               access_secret, skip_bbs, skip_live, skip_news, skip_video,
                               response_number_prefix, mark_hashes, slack_id))

        return result

# twitter
    def update_twitter_status(self, community, status):
        auth = tweepy.OAuthHandler(self.consumer_key[community], self.consumer_secret[community])
        auth.set_access_token(self.access_key[community], self.access_secret[community])

        # for test; simulating post error like case of api limit
        # raise TwitterStatusUpdateError

        try:
            tweepy.API(auth).update_status(status)
        except tweepy.error.TweepError, error:
            logging.error("twitter update error: %s" % error)
            # error.reason is the list object like following:
            #   [{"message":"Sorry, that page does not exist","code":34}]
            # see the following references for details:
            #   - https://dev.twitter.com/docs/error-codes-responses
            #   - ./tweepy/error.py

            # replace single quatation with double quatation to parse string properly
            normalized_reasons_string = re.sub("u'(.+?)'", r'"\1"', error.reason)

            reasons = None
            try:
                reasons = json.loads(normalized_reasons_string)
                # logging.debug("reasons: %s %s" % (type(reasons), reasons))
            except ValueError, error:
                # typically parse error like;
                # code 226 '"This request looks like it might be automated. ...'
                logging.warning("json parse error, the error will be handled as text, not json.")

            if reasons:
                for reason in reasons:
                    # logging.debug("reason: %s %s" % (type(reason), reason))
                    message = reason["message"]
                    code = reason["code"]
                    if reason["code"] == 187:
                        # 'Status is a duplicate.'
                        raise TwitterDuplicateStatusUpdateError(message, code)
                    elif reason["code"] == 186:
                        # 'Status is over 140 characters.'
                        raise TwitterOverCharactersStatusUpdateError(message, code)
                    elif reason["code"] == 185:
                        # 'User is over daily status update limit.'
                        raise TwitterOverUpdateLimitError(message, code)
            else:
                if re.search(r'might be automated', normalized_reasons_string):
                    # '"This request looks like it might be automated. ...'
                    raise TwitterSpamStatusUpdateError("possible spam")

            raise TwitterStatusUpdateError()

    def tweet_statuses(self, community, statuses, update_handler, update_target, tweet_count=0):
        for status in statuses:
            if 0 < tweet_count:
                logging.debug("sleeping %d secs before next tweet..." % TWEET_INTERVAL)
                time.sleep(TWEET_INTERVAL)

            try:
                self.update_twitter_status(community, status)
            except TwitterDuplicateStatusUpdateError, error:
                # status is already posted to twitter. so response status should be
                # changed from 'unprocessed' to other, in order to avoid reprocessing
                logging.error("twitter status update error, duplicate: %s" % error)
                update_handler(update_target, STATUS_DUPLICATE)
                break
            except TwitterOverUpdateLimitError, error:
                # quit this status update sequence
                logging.error("twitter status update error, over limit: %s" % error)
                raise
            except TwitterOverCharactersStatusUpdateError, error:
                # status has over 140 characters. this is possible nicobbs bug.
                logging.error("twitter status update error, over characters: %s" % error)
                update_handler(update_target, STATUS_OVER_CHARS)
                break
            except TwitterSpamStatusUpdateError, error:
                # spam rejected from twitter
                logging.error("twitter status update error, spam: %s" % error)
                update_handler(update_target, STATUS_SPAM)
                break
            except TwitterStatusUpdateError, error:
                # twitter error case including api limit
                # response status should not be changed here for future retrying
                logging.error("twitter status update error, unknown: %s" % error)
                break
            else:
                update_handler(update_target, STATUS_COMPLETED)
                logging.info("status updated: [%s]" % status)

            tweet_count += 1

        return tweet_count

# slack
    def post_response_to_slack(self, community, response):
        token = self.slack_token
        slack_id = self.slack_id[community]

        if token is None or slack_id is None:
            return

        sc = SlackClient(token)

        body = nicoutil.replace_body(response["body"])
        message = ("*(" + response["number"] + ":" + response["name"] +
                   ")*\n>>>" + body).encode("utf8")
        res = sc.api_call("chat.postMessage", channel=slack_id, text=message)
        logging.debug("slack response: %s" % res)
        time.sleep(1)

# network utility
    def create_opener(self):
        # cookie
        cookiejar = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
        # logging.debug("finished setting up cookie library")

        # login
        opener.open(LOGIN_URL, "mail=%s&password=%s" % (self.mail, self.password))
        logging.info("finished login")

        return opener

# message utility
    def prefilter_message(self, message):
        message = re.sub("<br/>", "\n", message)
        message = re.sub("<.*?>", "", message)
        message = re.sub("&gt;", ">", message)
        message = re.sub("&lt;", "<", message)
        message = re.sub("&amp;", "&", message)

        return message

    def postfilter_message(self, message):
        message = re.sub(u"\(省略しています。全て読むにはこのリンクをクリック！\)",
                         u"(省略)", message)
        message = re.sub(u"画像をクリックして再生!!",
                         u"(画像)", message)
        message = re.sub(u"この絵を基にしています！",
                         u"", message)
        message = re.sub(u"\n\n", u"\n", message)
        return message

# misc utility
    def find_community_name(self, rawhtml, community):
        soup = BeautifulSoup(rawhtml, 'html.parser')

        if self.is_channel(community):
            return soup.find("h1", {"class": "channel_name"}).text
        else:
            return soup.find("h1", {"id": "community_name"}).text

    def is_channel(self, community_id):
        return re.match(r'^co\d+$', community_id) is None

# mongo
    # response
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

    # news
    def register_news(self, news):
        self.database.news.update(
            {"community": news["community"], "date": news["date"]}, news, True)

    def is_news_registered(self, news):
        count = self.database.news.find(
            {"community": news["community"], "date": news["date"]}).count()
        return True if 0 < count else False

    def get_news_with_community_and_status(self, community, status):
        news = self.database.news.find({"community": community, "status": status})
        return news

    def update_news_status(self, news, status):
        self.database.news.update(
            {"community": news["community"], "date": news["date"]},
            {"$set": {"status": status}})

    # video
    def register_video(self, video):
        self.database.video.update(
            {"community": video["community"], "link": video["link"]}, video, True)

    def is_video_registered(self, video):
        count = self.database.video.find(
            {"community": video["community"], "link": video["link"]}).count()
        return True if 0 < count else False

    def get_video_with_community_and_status(self, community, status):
        videos = self.database.video.find({"community": community, "status": status})
        return videos

    def update_video_status(self, video, status):
        self.database.video.update(
            {"community": video["community"], "link": video["link"]},
            {"$set": {"status": status}})

# filter
    def contains_ng_words(self, message):
        for word in self.ng_words:
            if re.search(word, message):
                return True
        return False

    def contains_too_many_link(self, message):
        for regexp in SKIP_LINK_REGEXPS:
            matches = re.findall(regexp, message)
            if MAX_SKIP_LINKS_IN_RESPONSE < len(matches):
                return True
        return False

    def is_deleted_message(self, message):
        return message == DELETED_MESSAGE

# main
    # def page_number(self, strnum):
    #     intnum = int(strnum)
    #     return str(intnum - ((intnum-1) % 30))

# main, bbs
    def read_response_page(self, opener, community):
        url = COMMUNITY_BBS_URL + community
        if self.is_channel(community):
            url = CHANNEL_BASE_URL + community + '/bbs'
        logging.info("*** reading community bbs page, target: " + url)
        # logging.debug(url)

        reader = opener.open(url)
        rawhtml = reader.read()
        logging.debug("finished to read front page.")

        # print rawhtml
        # use scraping by regular expression, instead of by beautifulsoup.
        se = re.search('<iframe src="(http://dic\.nicovideo\.jp/.+?)"', rawhtml)
        internal_url = se.group(1)
        logging.debug("bbs internal url: " + internal_url)

        reader = opener.open(internal_url)
        rawhtml = reader.read()
        logging.info("finished to read bbs page.")
        # logging.debug(rawhtml)

        return rawhtml

    def parse_response(self, rawhtml, community):
        logging.info("*** parsing responses, community: %s" % community)

        soup = BeautifulSoup(rawhtml, 'html.parser')
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
            body = self.prefilter_message(body)
            # logging.debug(u"[%s] [%s] [%s] [\n%s\n]".encode('utf_8') %
            # (number, name, date, body))
            index += 1

            # if not self.is_valid_response(community, number):
            #     continue

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

        logging.info("scraped %s responses." % len(responses))

        return responses

    # quick workaround for broken bbs case
    def is_valid_response(self, community, number):
        number = int(number)

        # q, mokushiroku, yossan, noda
        has_valid_response_number = (
            (community == "co1827022" and 88680 < number and number < 95000) or
            (community == "gurikan" and 1130 < number and number < 2000) or
            (community == "co2427181" and 3300 < number and number < 5000) or
            (community == "co1354854" and 1600 < number and number < 3000))

        if has_valid_response_number:
            # logging.debug("response is valid.")
            pass
        else:
            logging.warning("response is NOT valid, should skip. %s,%s" % (community, number))

        return has_valid_response_number

    def store_response(self, responses, community):
        logging.info("*** storing responses, community: %s" % community)

        skipped_responses = []
        registered_responses = []

        for response in responses:
            response_number = "#%s" % response["number"]
            if self.is_response_registered(response):
                skipped_responses.append(response_number)
            else:
                self.register_response(response)
                registered_responses.append(response_number)

        logging.debug("skipped: %s" % skipped_responses)
        logging.debug("registered: %s" % registered_responses)
        logging.info("finished to store responses.")

    def deliver_response(self, community, response_number_prefix="", mark_hashes=[], limit=0):
        unprocessed_responses = self.get_responses_with_community_and_status(
            community, STATUS_UNPROCESSED)

        tweet_count = 0

        logging.info("*** processing responses, community: %s unprocessed: %d" %
                     (community, unprocessed_responses.count()))

        for response in unprocessed_responses:
            logging.debug("processing response #%s" % response["number"])
            self.post_response_to_slack(community, response)

            response_number = response_number_prefix + response["number"]
            response_name = response["name"]
            response_body = response["body"]
            response_hash = response["hash"]

            if (self.contains_ng_words(response_body) or
                    self.contains_too_many_link(response_body)):
                logging.debug(
                    "response contains ng word/too many video, so skip: [%s]" % response_body)
                self.update_response_status(response, STATUS_SPAM)
                continue

            if self.is_deleted_message(response_body):
                logging.debug("response is deleted, so skip: [%s]" % response_body)
                self.update_response_status(response, STATUS_DELETED)
                continue

            # create statuses
            response_body = self.postfilter_message(response_body)

            header = u'(' + response_number + u': ' + response_name + u')'
            if response_hash in mark_hashes:
                header += u' ★'
            header += u'\n'

            statuses = nicoutil.create_twitter_statuses(
                header, u'[続き] ', response_body, u' [続く]')

            tweet_count = self.tweet_statuses(
                community, statuses, self.update_response_status, response, tweet_count)

            if limit and limit <= tweet_count:
                logging.info("breaking tweet processing, limit: %d tweet_count: %d" %
                             (limit, tweet_count))
                break

        logging.info("finished to process responses.")

# main, reserved live
    def read_reserved_live_page(self, opener, community):
        url = COMMUNITY_TOP_URL + community
        if self.is_channel(community):
            url = CHANNEL_BASE_URL + community + '/live'
        logging.info("*** reading reserved live page, target: " + url)

        reader = opener.open(url)
        rawhtml = reader.read()
        # logging.debug(rawhtml)
        logging.info("finished to read reserved live page.")

        return rawhtml

    def parse_reserved_live(self, rawhtml, community):
        logging.info("*** parsing reserved lives, community: %s" % community)

        community_name = self.find_community_name(rawhtml, community)

        reserved_lives = []
        soup = BeautifulSoup(rawhtml, 'html.parser')

        if self.is_channel(community):
            section = soup.find("section", {"class": "future"})
            if section:
                lives = section.find_all("div", {"class": "item_right"})
                for live in lives:
                    title = live.find("h2", {"class": "title"})
                    link = title.find("a")["href"]
                    date = live.find("p", {"class": "date"}).text
                    reserved_live = {"community": community,
                                     "community_name": community_name,
                                     "title": title.text,
                                     "link": link,
                                     "date": date,
                                     "status": STATUS_UNPROCESSED}
                    reserved_lives.append(reserved_live)
        else:
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
                                         "community_name": community_name,
                                         "title": anchor.text,
                                         "link": link,
                                         "date": date.text,
                                         "status": STATUS_UNPROCESSED}
                        reserved_lives.append(reserved_live)

        logging.info("scraped %s reserved lives." % len(reserved_lives))

        return reserved_lives

    def store_reserved_live(self, reserved_lives, community):
        logging.info("*** storing reserved lives, community: %s" % community)

        for reserved_live in reserved_lives:
            if self.is_live_registered(reserved_live):
                logging.debug("skipped: %s" % reserved_live["link"])
            else:
                self.register_live(reserved_live)
                logging.debug("registered: %s" % reserved_live["link"])

        logging.info("finished to store reserved lives.")

    def tweet_reserved_live(self, community, limit=0):
        unprocessed_lives = self.get_lives_with_community_and_status(
            community, STATUS_UNPROCESSED)
        tweet_count = 0

        logging.info("*** processing lives, community: %s unprocessed: %d" %
                     (community, unprocessed_lives.count()))

        for live in unprocessed_lives:
            logging.debug("processing live %s" % live["link"])

            status = (u"【放送予約】「" + live["community_name"] + u"」で生放送「" +
                      live["title"] + u"」が予約されました。" + live["date"] + u" " +
                      live["link"])

            tweet_count = self.tweet_statuses(
                    community, [status], self.update_live_status, live, tweet_count)

            if limit and limit <= tweet_count:
                logging.info("breaking tweet processing, limit: %d tweet_count: %d" %
                             (limit, tweet_count))
                break

        logging.info("finished to process reserved lives.")

# main, news
    def parse_news(self, rawhtml, community):
        logging.info("*** parsing community news, community: %s" % community)

        community_name = self.find_community_name(rawhtml, community)

        news_items = []
        soup = BeautifulSoup(rawhtml, 'html.parser')

        community_news_tag = soup.find(id="community_news")
        if community_news_tag:
            items = community_news_tag.select(".item")
            for item in items:
                title = item.select(".title")[0].get_text()
                desc = item.select(".desc")[0].get_text()
                desc = self.prefilter_message(desc)

                date_and_name = item.select(".date")[0].get_text()
                date = None
                name = None
                matched = re.match(ur'(.+)（(.+)）', date_and_name)
                if matched:
                    date = matched.group(1)
                    name = matched.group(2)

                news_item = {"community": community,
                             "community_name": community_name,
                             "title": title,
                             "desc": desc,
                             "date": date,
                             "name": name,
                             "status": STATUS_UNPROCESSED}
                news_items.append(news_item)

        logging.info("scraped %s news." % len(news_items))

        return news_items

    def store_news(self, news_items, community):
        logging.info("*** crawling news, community: %s" % community)

        for news_item in news_items:
            if self.is_news_registered(news_item):
                logging.debug("skipped: %s" % news_item["date"])
            else:
                self.register_news(news_item)
                logging.debug("registered: %s" % news_item["date"])

        logging.info("finished to crawl news")

    def tweet_news(self, community, limit=0):
        unprocessed_news = self.get_news_with_community_and_status(
            community, STATUS_UNPROCESSED)
        tweet_count = 0

        logging.info("*** processing news, community: %s unprocessed: %d" %
                     (community, unprocessed_news.count()))

        for news in unprocessed_news:
            logging.debug("processing news %s" % news["date"])

            statuses = nicoutil.create_twitter_statuses(
                u"【お知らせ更新】\n" +
                u"「%s」(%s)\n\n" % (news["title"], news["name"]),
                u'[続き] ', news["desc"], u' [続く]')

            tweet_count = self.tweet_statuses(
                community, statuses, self.update_news_status, news, tweet_count)

            if limit and limit <= tweet_count:
                logging.info("breaking tweet processing, limit: %d tweet_count: %d" %
                             (limit, tweet_count))
                break

        logging.info("finished to process news")

# main, video
    def read_video_page(self, opener, community):
        url = COMMUNITY_VIDEO_URL + community
        logging.info("*** reading video page, target: " + url)

        reader = opener.open(url)
        rawhtml = reader.read()
        # logging.debug(rawhtml)
        logging.info("finished to read video page.")

        return rawhtml

    def parse_video(self, rawhtml, community):
        logging.info("*** parsing community video, community: %s" % community)

        videos = []
        soup = BeautifulSoup(rawhtml, 'html.parser')
        video_tag = soup.find(id="video")

        if video_tag:
            items = video_tag.select(".video")
            for item in items:
                title = item.get_text()
                link = item["href"]

                video = {"community": community,
                         "title": title,
                         "link": link,
                         "status": STATUS_UNPROCESSED}
                videos.append(video)

        logging.info("scraped %s videos." % len(videos))

        return videos

    def store_video(self, videos, community):
        logging.info("*** crawling video, community: %s" % community)

        for video in videos:
            if self.is_video_registered(video):
                logging.debug("skipped: %s" % video["link"])
            else:
                self.register_video(video)
                logging.debug("registered: %s" % video["link"])

        logging.info("finished to crawl video")

    def tweet_video(self, community, limit=0):
        unprocessed_videos = self.get_video_with_community_and_status(
            community, STATUS_UNPROCESSED)
        tweet_count = 0

        logging.info("*** processing video, community: %s unprocessed: %d" %
                     (community, unprocessed_videos.count()))

        for video in unprocessed_videos:
            logging.debug("processing video %s" % video["link"])

            statuses = nicoutil.create_twitter_statuses(
                u"【コミュ動画投稿】",
                u'[続き] ',
                u"「%s」が投稿されました。%s" % (video["title"], video["link"]),
                u' [続く]')

            tweet_count = self.tweet_statuses(
                community, statuses, self.update_video_status, video, tweet_count)

            if limit and limit <= tweet_count:
                logging.info("breaking tweet processing, limit: %d tweet_count: %d" %
                             (limit, tweet_count))
                break

        logging.info("finished to process video")

# kick
    def kick_bbs(self, opener, community, response_number_prefix="", mark_hashes=[]):
        try:
            rawhtml = self.read_response_page(opener, community)
            responses = self.parse_response(rawhtml, community)
            self.store_response(responses, community)
            self.deliver_response(community, response_number_prefix, mark_hashes)
        except TwitterOverUpdateLimitError:
            raise
        except urllib2.HTTPError, error:
            logging.error("*** caught http error when processing bbs, error: %s" % error)
            if error.code == 403:
                logging.info("bbs is closed?")
        except Exception, error:
            logging.error("*** caught error when processing bbs, error: %s" % error)

    def kick_live_news(self, opener, community):
        try:
            rawhtml = self.read_reserved_live_page(opener, community)

            if self.skip_live[community]:
                logging.info("skipped live.")
            else:
                reserved_lives = self.parse_reserved_live(rawhtml, community)
                self.store_reserved_live(reserved_lives, community)
                self.tweet_reserved_live(community)

            if self.skip_news[community]:
                logging.info("skipped news.")
            else:
                if self.is_channel(community):
                    logging.info("channel news is not supported, so skip.")
                    return

                # use rawhtml above
                news_items = self.parse_news(rawhtml, community)
                self.store_news(news_items, community)
                self.tweet_news(community)
        except TwitterOverUpdateLimitError:
            raise
        except Exception, error:
            logging.error("*** caught error when processing live/news, error: %s" % error)

    def kick_video(self, opener, community):
        if self.is_channel(community):
            logging.info("channel video is not supported, so skip.")
            return

        try:
            rawhtml = self.read_video_page(opener, community)
            videos = self.parse_video(rawhtml, community)
            self.store_video(videos, community)
            self.tweet_video(community)
        except TwitterOverUpdateLimitError:
            raise
        except Exception, error:
            logging.error("*** caught error when processing video, error: %s" % error)

    def start(self):
        # inifinite loop
        while True:
            try:
                logging.debug(LOG_SEPARATOR)
                opener = self.create_opener()
            except Exception, error:
                logging.error("*** caught error when creating opener, error : %s" % error)
            else:
                for community in self.target_communities:
                    logging.debug(LOG_SEPARATOR)
                    logging.info("*** " + community)
                    try:
                        if self.skip_bbs[community]:
                            logging.info("skipped bbs.")
                        else:
                            self.kick_bbs(opener,
                                          community,
                                          self.response_number_prefix[community],
                                          self.mark_hashes[community])

                        if self.skip_live[community] and self.skip_news[community]:
                            logging.info("skipped live and news.")
                        else:
                            self.kick_live_news(opener, community)

                        if self.skip_video[community]:
                            logging.info("skipped video.")
                        else:
                            self.kick_video(opener, community)
                    except TwitterOverUpdateLimitError:
                        logging.warning("status update over limit, so skip.")
                    logging.debug("*** sleeping %d secs..." % COMMUNITY_INTERVAL)
                    time.sleep(COMMUNITY_INTERVAL)

            logging.debug(LOG_SEPARATOR)
            logging.debug("*** sleeping %d secs..." % CRAWL_INTERVAL)
            time.sleep(CRAWL_INTERVAL)


if __name__ == "__main__":
    nicobbs = NicoBBS()
    nicobbs.start()
