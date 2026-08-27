"""Request-scoped timezone activation.

Datetimes are stored in UTC. Django renders them, and interprets naive form
input, in the *active* timezone, which defaults to settings.TIME_ZONE. Without
this middleware every visitor sees Davis time, and a naive value submitted from
anywhere east of Davis is parsed as Davis time, lands in the future, and is
rejected by Match.clean().

The browser reports its own zone in a cookie (see base_html.html).
"""

from urllib.parse import unquote
from zoneinfo import ZoneInfo, available_timezones

from django.utils import timezone

TIMEZONE_COOKIE_NAME = "tz"


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # available_timezones() walks the tzdata database, so resolve the set of
        # valid names once at startup instead of on every request.
        self.valid_names = available_timezones()

    def __call__(self, request):
        name = request.COOKIES.get(TIMEZONE_COOKIE_NAME)
        # Django's parse_cookie resolves RFC 2109 escapes but never
        # percent-decodes, so a value written with encodeURIComponent arrives as
        # "America%2FSao_Paulo". unquote is a no-op on a raw IANA name.
        if name:
            name = unquote(name)
        # The cookie is client-supplied, so an unknown name is expected input
        # rather than an exceptional case. ZoneInfo would raise
        # ZoneInfoNotFoundError and turn it into a 500 on every page.
        if name in self.valid_names:
            timezone.activate(ZoneInfo(name))
        else:
            timezone.deactivate()
        try:
            return self.get_response(request)
        finally:
            # The active timezone is thread-local and workers are reused, so
            # leaving it set would leak one visitor's zone into the next request
            # handled by the same thread.
            timezone.deactivate()
