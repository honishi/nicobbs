#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime as dt

import nicobbs


DUMMY_CREDENTIAL_KEY = "dummy"


def pytest_funcarg__bbs(request):
    bbs = nicobbs.NicoBBS(is_test=True)

    # inject twitter credentials to bbs instance
    bbs.consumer_key[DUMMY_CREDENTIAL_KEY] = os.environ.get("CONSUMER_KEY")
    bbs.consumer_secret[DUMMY_CREDENTIAL_KEY] = os.environ.get("CONSUMER_SECRET")
    bbs.access_key[DUMMY_CREDENTIAL_KEY] = os.environ.get("ACCESS_KEY")
    bbs.access_secret[DUMMY_CREDENTIAL_KEY] = os.environ.get("ACCESS_SECRET")

    return bbs


def test_tweet(bbs):
    bbs.update_twitter_status(DUMMY_CREDENTIAL_KEY, u'テスト from nicobbs (%s)' % dt.now())
    assert True
