#!/bin/env python
# -*- coding: utf-8 -*-

# import sys, codecs, time, random, re, datetime, dateutil.parser, threading
import sys
# import tweepy, urllib, urllib2, json
import tweepy
import ConfigParser

from os import path

root_path = path.dirname(path.abspath(__file__))
twitter_config = root_path + '/' + 'twitter.config'

class twitter:
# class lifecycle
    def __init__(self):
        self.api = self.open_api()
        return

    def __del__(self):
        pass

# main
    def open_api(self):
        config = ConfigParser.ConfigParser()
        config.read(twitter_config)
        consumer_key = config.get("twitter", "consumer_key")
        consumer_secret = config.get("twitter", "consumer_secret")
        access_key = config.get("twitter", "access_key")
        access_secret = config.get("twitter", "access_secret")

        # print "consumer_key: %s" % consumer_key
        # print "consumer_secret: %s" % consumer_secret
        # print "access_key: %s" % access_key
        # print "access_secret: %s" % access_secret

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_key, access_secret)
        return tweepy.API(auth)

    def update_status(self, status):
        try:
          self.api.update_status(status)
        except tweepy.error.TweepError, error:
          print u'error in post.'
          print error

    def remove_all(self):
        for status in tweepy.Cursor(self.api.user_timeline).items(1000):
            try:
                self.api.destroy_status(status.id)
            except tweepy.error.TweepError, error:
                print u'error in post destroy'
                print error
            sys.stdout.flush()

if __name__ == "__main__":
    twitter = twitter()
    twitter.update_status("テスト")
