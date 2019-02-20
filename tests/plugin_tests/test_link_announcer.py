import codecs

from bs4 import BeautifulSoup
from responses import RequestsMock
from mock import MagicMock
from plugins.link_announcer import url_re, get_encoding, print_url_title
import pytest

MATCHES = (
    "http://foo.com/blah_blah",
    "http://foo.com/blah_blah/",
    "http://foo.com/blah_blah_(wikipedia)",
    "http://foo.com/blah_blah_(wikipedia)_(again)",
    "http://www.example.com/wpstyle/?p=364",
    "https://www.example.com/foo/?bar=baz&inga=42&quux",
    "http://userid:password@example.com:8080",
    "http://userid:password@example.com:8080/",
    "http://userid@example.com",
    "http://userid@example.com/",
    "http://userid@example.com:8080",
    "http://userid@example.com:8080/",
    "http://userid:password@example.com",
    "http://userid:password@example.com/",
    "http://142.42.1.1/",
    "http://142.42.1.1:8080/",
    "http://foo.com/blah_(wikipedia)#cite-1",
    "http://foo.com/blah_(wikipedia)_blah#cite-1",
    "http://foo.com/unicode_(✪)_in_parens",
    "http://foo.com/(something)?after=parens",
    "http://code.google.com/events/#&product=browser",
    "http://j.mp",
    "http://foo.bar/?q=Test%20URL-encoded%20stuff",
    "http://1337.net",
    "http://a.b-c.de",
    "http://223.255.255.254",
    "https://foo.bar/baz?#",
    "https://foo.bar/baz?",
)

FAILS = (
    "http://",
    "http://.",
    "http://..",
    "http://?",
    "http://??",
    "http://??/",
    "http://#",
    "http://##",
    "http://##/",
    "http://foo.bar?q=Spaces should be encoded",
    "//",
    "//a",
    "///a",
    "///",
    "http:///a",
    "foo.com",
    "rdar://1234",
    "h://test",
    "http:// shouldfail.com",
    ":// should fail",
    "http://foo.bar/foo(bar)baz quux",
    "ftps://foo.bar/",
    "https://foo.bar/baz.ext)",
    "https://foo.bar/test.",
    "https://foo.bar/test(test",
    "https://foo.bar.",
    "https://foo.bar./",
)

SEARCH = (
    ("(https://foo.bar)", "https://foo.bar"),
    ("[https://example.com]", "https://example.com"),
    ("<a hreh=\"https://example.com/test.page?#test\">", "https://example.com/test.page?#test"),
    ("<https://www.example.com/this.is.a.test/blah.txt?a=1#123>",
     "https://www.example.com/this.is.a.test/blah.txt?a=1#123"),
)


def test_urls():
    for url in MATCHES:
        assert url_re.fullmatch(url), url

    for url in FAILS:
        match = url_re.fullmatch(url)
        assert not match, match.group()


def test_search():
    for text, out in SEARCH:
        match = url_re.search(text)
        assert match and match.group() == out


ENCODINGS = (
    (b'<meta charset="utf8">', codecs.lookup('utf8')),
    (b'', None),
    (b'<meta http-equiv="Content-Type" content="text/html; charset=utf-8">', codecs.lookup('utf8')),
)


def test_encoding_parse():
    for text, enc in ENCODINGS:
        soup = BeautifulSoup(text, "lxml")
        encoding = get_encoding(soup)
        if encoding is None:
            assert enc is None, "Got empty encoding from {!r} expected {!r}".format(text, enc)
            continue

        enc_obj = codecs.lookup(encoding)

        assert enc, enc_obj


STD_HTML = "<head><title>{}</title></head>"
TESTS = {
    "http://www.montypython.fun": ("<!DOCTYPE html><head><title>{}</title></head><body>test</body>", "This Site is dead."),
    "http://www.talos.principle": (STD_HTML, "In the beginning were the words"),
    "http://www.nonexistent.lol": ("", False),
    "http://www.much-newlines.backslashn": (("\n" * 500) + STD_HTML, "new lines!"),
    "http://completely.invalid": ("\x01\x01\x02\x03\x05\x08\x13", False),
    "http://large.amounts.of.text": (STD_HTML + ("42"*512*4096) + "</body>", "here have a couple megs of text"),
    "http://star.trek.the.next.title": (STD_HTML, "47" * 512 * 4096),
    "http://bare.title": ("<title>{}</title>", "here has title")
}


@pytest.mark.parametrize(
    "match,test_str,res",
    [(url_re.search(a), b.format(c), c) for a, (b, c) in TESTS.items()]
)
def test_link_announce(match, test_str, res):
    with RequestsMock() as reqs:
        reqs.add(RequestsMock.GET, match.string, body=test_str, stream=True)
        mck = MagicMock()

        print_url_title(match=match, message=mck)
        if res and len(test_str) < 1_000_000:
            mck.assert_called_with("Title: \x02" + res + "\x02")
        else:
            mck.assert_not_called()


