# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from werkzeug import urls


def get_url(url: str, page: int, url_args: dict) -> str:
    """
    Constructs a URL using a set of parameters for a paging object.
    :param url: the base URL
    :type url: str
    :param page: the number of current page
    :type page: int
    :param url_args: the extra arguments dictionary
    :type url_args: dict
    :return: a URL with the parameters encoded
    :rtype: str
    """
    _url = "%s/page/%s" % (url, page) if page > 1 else url
    if url_args:
        _url = "%s?%s" % (_url, urls.url_encode(url_args))
    return _url
