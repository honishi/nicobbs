#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime as dt

import nicobbs


TEST_MAIL = os.environ.get("NICO_MAIL")
TEST_PASSWORD = os.environ.get("NICO_PASSWORD")

TEST_CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
TEST_CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
TEST_ACCESS_KEY = os.environ.get("ACCESS_KEY")
TEST_ACCESS_SECRET = os.environ.get("ACCESS_SECRET")

TEST_DATABASE_NAME = os.environ.get("DATABASE_NAME")
TEST_COMMUNITY_ID = os.environ.get("COMMUNITY_ID")

DUMMY_COMMUNITY_TOP_PAGE = (os.path.dirname(os.path.abspath(__file__)) +
                            '/dummy_community_top_page.html')


# create instance & inject setting
def pytest_funcarg__bbs(request):
    unused_request = request

    bbs = nicobbs.NicoBBS(is_test=True)

    bbs.mail = TEST_MAIL
    bbs.password = TEST_PASSWORD

    bbs.consumer_key[TEST_COMMUNITY_ID] = TEST_CONSUMER_KEY
    bbs.consumer_secret[TEST_COMMUNITY_ID] = TEST_CONSUMER_SECRET
    bbs.access_key[TEST_COMMUNITY_ID] = TEST_ACCESS_KEY
    bbs.access_secret[TEST_COMMUNITY_ID] = TEST_ACCESS_SECRET

    bbs.target_communities = [TEST_COMMUNITY_ID]
    bbs.database_name = TEST_DATABASE_NAME

    bbs.database = bbs.connection[bbs.database_name]

    return bbs


def test_main(bbs):
    bbs.start(2)


# reserved live should be test using dummy static content
# because it usually not be provided at real community page
def test_live_and_news(bbs):
    for community in bbs.target_communities:
        # reserved live & news
        f = open(DUMMY_COMMUNITY_TOP_PAGE)
        rawhtml = f.read()
        f.close()
        assert rawhtml is not None

        bbs.crawl_reserved_live(rawhtml, community)
        bbs.tweet_reserved_live(community, 2)
        bbs.crawl_news(rawhtml, community)
        bbs.tweet_news(community, 2)

    assert True


def test_tweet(bbs):
    bbs.update_twitter_status(TEST_COMMUNITY_ID, u'テスト from nicobbs (%s)' % dt.now())
    assert True
