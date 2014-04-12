#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime as dt
import re

import nicobbs


TEST_MAIL = os.environ.get("NICO_MAIL")
TEST_PASSWORD = os.environ.get("NICO_PASSWORD")

TEST_CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
TEST_CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
TEST_ACCESS_KEY = os.environ.get("ACCESS_KEY")
TEST_ACCESS_SECRET = os.environ.get("ACCESS_SECRET")

TEST_DATABASE_NAME = os.environ.get("DATABASE_NAME")

TEST_COMMUNITY_BBS_PAGE = (os.path.dirname(os.path.abspath(__file__)) + '/community_bbs.html')
TEST_COMMUNITY_TOP_PAGE = (os.path.dirname(os.path.abspath(__file__)) + '/community_top.html')
TEST_COMMUNITY_VIDEO_PAGE = (os.path.dirname(os.path.abspath(__file__)) + '/community_video.html')
TEST_CHANNEL_LIVE_PAGE = (os.path.dirname(os.path.abspath(__file__)) + '/channel_live.html')


# create instance & inject setting
def pytest_funcarg__bbs(request):
    unused_request = request

    bbs = nicobbs.NicoBBS()

    bbs.mail = TEST_MAIL
    bbs.password = TEST_PASSWORD

    bbs.target_communities = ['co1234', 'abcdef']

    for community in bbs.target_communities:
        bbs.consumer_key[community] = TEST_CONSUMER_KEY
        bbs.consumer_secret[community] = TEST_CONSUMER_SECRET
        bbs.access_key[community] = TEST_ACCESS_KEY
        bbs.access_secret[community] = TEST_ACCESS_SECRET

    bbs.database_name = TEST_DATABASE_NAME
    bbs.database = bbs.connection[bbs.database_name]

    return bbs


def test_is_channel(bbs):
    assert bbs.is_channel('co1234') is False
    assert bbs.is_channel('abcdef') is True


def read_test_page(path):
    f = open(path)
    content = f.read()
    f.close()

    return content


#def test_read_response(bbs):
#    opener = bbs.create_opener()
#
#    html = bbs.read_response_page(opener, 'co1827022')    # ankoku q
#    # print(html)
#    assert re.search(r'ななしのよっしん', html) is not None
#
#    html = bbs.read_response_page(opener, 'gurikan')    # ankoku mokushiroku
#    # print(html)
#    assert re.search(r'ななしのよっしん', html) is not None


def test_response(bbs):
    community = 'co1234'
    html = read_test_page(TEST_COMMUNITY_BBS_PAGE)
    assert html is not None

    responses = bbs.parse_response(html, community)
    assert 0 < len(responses)

    response = responses[0]
    assert 0 < len(response['community'])
    assert 0 < len(response['number'])
    assert 0 < len(response['name'])
    assert 0 < len(response['date'])
    assert 0 < len(response['hash'])
    assert 0 < len(response['body'])
    assert 0 < len(response['status'])

    bbs.store_response(responses, community)
    # bbs.tweet_response(community, limit=2)


#def test_read_live(bbs):
#    opener = bbs.create_opener()
#
#    html = bbs.read_reserved_live_page(opener, 'co1827022')    # ankoku q
#    # print(html)
#    assert re.search(r'予約スケジュール', html) is not None
#
#    html = bbs.read_reserved_live_page(opener, 'gurikan')    # ankoku mokushiroku
#    # print(html)
#    assert re.search(r'放送予定', html) is not None


def test_find_community_name(bbs):
    community = 'co1234'
    html = read_test_page(TEST_COMMUNITY_TOP_PAGE)
    assert html is not None

    community_name = bbs.find_community_name(html, community)
    assert community_name == u"ちーめろでぃの『Tea ＆ Melody♫』(*･ω･)っ旦"

    community = 'abcdef'
    html = read_test_page(TEST_CHANNEL_LIVE_PAGE)
    assert html is not None

    community_name = bbs.find_community_name(html, community)
    assert community_name == u"ニコプロ -ニコニコプロレスチャンネル-"


def test_live_user(bbs):
    community = 'co1234'
    html = read_test_page(TEST_COMMUNITY_TOP_PAGE)
    assert html is not None

    lives = bbs.parse_reserved_live(html, community)
    assert 0 < len(lives)

    live = lives[0]
    assert 0 < len(live['community'])
    assert 0 < len(live['link'])
    assert 0 < len(live['community_name'])
    assert 0 < len(live['date'])
    assert 0 < len(live['title'])
    assert 0 < len(live['status'])

    bbs.store_reserved_live(lives, community)
    # bbs.tweet_reserved_live(community, limit=2)


def test_live_channel(bbs):
    community = 'abcdef'
    html = read_test_page(TEST_CHANNEL_LIVE_PAGE)
    assert html is not None

    lives = bbs.parse_reserved_live(html, community)
    assert 0 < len(lives)

    live = lives[0]
    assert 0 < len(live['community'])
    assert 0 < len(live['link'])
    assert 0 < len(live['community_name'])
    assert 0 < len(live['date'])
    assert 0 < len(live['title'])
    assert 0 < len(live['status'])

    bbs.store_reserved_live(lives, community)
    # bbs.tweet_reserved_live(community, limit=2)


def test_news(bbs):
    community = 'co1234'
    html = read_test_page(TEST_COMMUNITY_TOP_PAGE)
    assert html is not None

    news_items = bbs.parse_news(html, community)
    assert 0 < len(news_items)

    news = news_items[0]
    assert 0 < len(news['community'])
    assert 0 < len(news['community_name'])
    assert 0 < len(news['title'])
    assert 0 < len(news['desc'])
    assert 0 < len(news['date'])
    assert 0 < len(news['name'])
    assert 0 < len(news['status'])

    bbs.store_news(news_items, community)
    # bbs.tweet_news(community, limit=2)


def test_video(bbs):
    community = 'co1234'
    html = read_test_page(TEST_COMMUNITY_VIDEO_PAGE)
    assert html is not None

    videos = bbs.parse_video(html, community)
    assert 0 < len(videos)

    video = videos[0]
    assert 0 < len(video['community'])
    assert 0 < len(video['title'])
    assert 0 < len(video['link'])
    assert 0 < len(video['status'])

    bbs.store_video(videos, community)
    # bbs.tweet_video(community, limit=2)


#def test_tweet(bbs):
#    bbs.update_twitter_status(TEST_COMMUNITY_ID, u'テスト from nicobbs (%s)' % dt.now())
#    assert True
