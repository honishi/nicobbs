#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

TWITTER_STATUS_MAX_LENGTH = 140
TCO_URL_LENGTH = 23

REGEXP_VIDEO = r'sm\d{3,}'
REGEXP_LIVE = r'lv\d{3,}'
BASE_URL_VIDEO = u'http://www.nicovideo.jp/watch/'
BASE_URL_LIVE = u'http://live.nicovideo.jp/watch/'

# regexp for http(s), http://www.megasoft.co.jp/mifes/seiki/s310.html
# regexp for twitter account, http://stackoverflow.com/a/4424288
REGEXP_HTTP = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
REGEXP_TWITTER = r'@[A-Za-z0-9_]{1,15}'

# replace twitter's @account with !account
ENABLE_MASKING_TWITTER = True
REGEXP_TWITTER_REPLACE_FROM = r'@([A-Za-z0-9_]{1,15})'
REGEXP_TWITTER_REPLACE_TO = r'!\1'

CHUNK_TYPE_UNKNOWN = 1
CHUNK_TYPE_TEXT = 2
CHUNK_TYPE_HTTP = 3
CHUNK_TYPE_TWITTER = 4


# internal methods
def create_finalized_statuses(status_bodies, header, continued_mark, continue_mark):
    finalized_statuses = []
    status_bodies_count = len(status_bodies)

    index = 0
    for status_body in status_bodies:
        if ENABLE_MASKING_TWITTER:
            status_body = re.sub(
                REGEXP_TWITTER_REPLACE_FROM, REGEXP_TWITTER_REPLACE_TO, status_body)
        if status_bodies_count == 1:
            status = header + status_body
        else:
            if index == 0:
                status = header + status_body + continue_mark
            elif index < status_bodies_count - 1:
                status = header + continued_mark + status_body + continue_mark
            else:
                status = header + continued_mark + status_body
        finalized_statuses.append(status)
        index += 1

    return finalized_statuses


# public methods
def create_twitter_statuses(header, continued_mark, body, continue_mark):
    available_length = TWITTER_STATUS_MAX_LENGTH - len(header + continued_mark + continue_mark)
    # print available_length

    # print 'before replace: [' + body + ']'
    body = re.sub(r'(' + REGEXP_VIDEO + r')', BASE_URL_VIDEO + r'\1', body)
    body = re.sub(r'(' + REGEXP_LIVE + r')', BASE_URL_LIVE + r'\1', body)
    body = re.sub(r'\n+$', '', body)
    # print 'after replace: [' + body + ']'

    statuses_with_body = []
    status_buffer = u""
    chunk_type = CHUNK_TYPE_UNKNOWN
    remaining_length = available_length

    regexp = u'(%s|%s)' % (REGEXP_HTTP, REGEXP_TWITTER)
    chunks = re.split(regexp, body)

    for chunk in chunks:
        # print u'chunk: [' + chunk + u']'
        # print u'remaining_length, pre-processed: %d' % remaining_length

        chunk_length = 0
        if re.match(REGEXP_HTTP, chunk):
            chunk_type = CHUNK_TYPE_HTTP
            chunk_length = TCO_URL_LENGTH
        elif re.match(REGEXP_TWITTER, chunk):
            chunk_type = CHUNK_TYPE_TWITTER
            chunk_length = len(chunk)
        else:
            chunk_type = CHUNK_TYPE_TEXT

        if chunk_type in [CHUNK_TYPE_HTTP, CHUNK_TYPE_TWITTER]:
            if chunk_length <= remaining_length:
                status_buffer += chunk
                remaining_length -= chunk_length
            else:
                statuses_with_body.append(status_buffer)
                status_buffer = chunk
                remaining_length = available_length - chunk_length
        elif chunk_type == CHUNK_TYPE_TEXT:
            while len(chunk):
                breaking_chunk = chunk[0:remaining_length]
                chunk = chunk[remaining_length:]

                status_buffer += breaking_chunk
                remaining_length -= len(breaking_chunk)

                if not remaining_length:
                    statuses_with_body.append(status_buffer)
                    status_buffer = u""
                    remaining_length = available_length
        # print u'remaining_length, post-processed: %d' % remaining_length

    if len(status_buffer):
        statuses_with_body.append(status_buffer)
        status_buffer = u""
        remaining_length = available_length

    return create_finalized_statuses(statuses_with_body, header, continued_mark, continue_mark)

if __name__ == "__main__":
    original_body = """\
　あるところに、牛を持っている百姓がありました。その牛は、もう年をとっていました。長い年の間、その百姓のために重い荷をつけて働いたのであります。そして、いまでも、なお働いていたのであったけれど、なんにしても、年をとってしまっては、ちょうど人間と同じように、若い時分ほど働くことはできなかったのです。
　この無理もないことを、百姓はあわれとは思いませんでした。そして、いままで自分たちのために働いてくれた牛を、大事にしてやろうとは思わなかったのであります。
「こんな役にたたないやつは、早く、どこかへやってしまって、若いじょうぶな牛と換えよう。」と思いました。
　秋の収穫もすんでしまうと、来年の春まで、地面は、雪や、霜のために堅く凍ってしまいますので、牛を小舎の中に入れておいて、休ましてやらなければなりません。この百姓は、せめて牛をそうして、春まで休ませてやろうともせずに、
「冬の間こんな役にたたないやつを、食べさしておくのはむだな話だ。」といって、たとえ、ものこそいわないけれど、なんでもよく人間の感情はわかるものを、このおとなしい牛をひどいめにあわせたのであります。
　ある、うす寒い日のこと、百姓は、話に、馬の市が四里ばかり離れた、小さな町で開かれたということを聞いたので、喜んで、小舎の中から、年とった牛を引き出して、若い牛と交換してくるために町へと出かけたのでした。
　百姓は、自分たちといっしょに苦労をした、この年をとった牛に分かれるのを、格別悲しいとも感じなかったのであるが、牛は、さもこの家から離れてゆくのが悲しそうに見えて、なんとなく、歩く足つきも鈍かったのでありました。
"""
    test_body = """\
　あるところに、牛を持っている百姓がありました。その牛は、もう年をとっていました。長い年の間、その百姓のために重い荷をつけて働いたのであります。そして、いまでも、なお働いていたのであったけれど、なんにしても、年をとってしまっては、@abcdちょうど人間と同じように、若い時分ほど働くことはできなかったのです。
　この無理もないことを、百姓はあわれとは思いませんでした。そして、いままで自分たちのために働いてくれた牛を、大事にしてやろうとは思わなかったのでhttp://example.comあります。
「こんな役にたたないやつは、早く、どこかへやってしまって、若いじょうぶな牛と換えよう。」と思いました。
　秋の収穫もすんでしまうと、来年の春まで、地面は、雪や、霜のために堅く凍ってしまいますので、https://example.co.jp/aaaaaaaaaa/aaaaaaaaaa/aaaaaaaaaa牛を小舎の中に入れておいて、休ましてやらなければなりません。この百姓は、せめて牛をそうして、aa春まで休ませてやろうともせずに、
「http://example.com/bbbbbbbbbb/bbbbbbbbbb冬の間こんな役にたたないやつを、食べさしておくのはむだな話だ。」といって、たとえ、ものこそいわないけれど、なんでもよく人間の感情はわかるものを、このおとなしい牛をひどいめにあわせたのであります。
　ある、うす寒い日のこと、百姓は、話に、馬の市が四里ばかり離れた、小さな町で開かれたということを聞いたので、喜んで、小舎の中から、年とった牛を引き出して、若い牛と交換してくるために町へと出かけたのでした。
　百姓は、自分たちといっしょに苦労をした、この年をとった牛に分かれるのを、格別悲しいとも感じなかったのであるが、牛は、さもこの家から離れてゆくのが悲しそうに見えて、なんとなく、歩く足つきも鈍かったのでありました。
"""
    short_body = """\
　あるところに、牛を持っている百姓がありました。その牛は、もう年をとっていました。長い年の間、その百姓のために重い荷をつけて働いたのであります。そして、いまでも、なお働いていたのであったけれど、なんにしても、
"""
    http_body = """\
　あるところに、牛を持っている百姓がありました。その牛は、もう年をとっていました。長い年の間、その百姓のために重い荷をつけて働いたのであります。そして、いまでも、なお働いていたのであった。
http://www.chikuwachan.com/live/catalog/index.cgi?category=&sort=room2&rev=co10000
"""
    http_nico_url = """\
sm123 lv123
"""
    # target_body = original_body
    target_body = test_body
    # target_body = short_body
    # target_body = http_body
    # target_body = http_nico_url

    # need to convert body from str type to unicode type
    target_body = target_body.decode('UTF-8')
    print type(target_body)

    statuses = create_twitter_statuses(
        u"(ななしのよっしん)\n", u"[続き] ", target_body, u" [続く]")

    index = 0
    for status in statuses:
        print u"*** index: %d length: %d status: [%s]\n" % (index, len(status), status)
        index += 1
