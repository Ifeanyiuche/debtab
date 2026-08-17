"""
Health check endpoint.

The point of this file: the June outage was invisible because nothing ever
touched the database except a logged-in user's request. The homepage and the
login form both render fine with a completely dead database, so the site looked
healthy from the outside while being unusable. This endpoint makes the database
part of what "up" means, so an uptime monitor notices within minutes instead of
a user noticing weeks later.

It also doubles as a keep-alive: free-tier databases and web services suspend
themselves after a period of inactivity, and a monitor hitting this URL on a
schedule keeps both awake.
"""

import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def healthz(request):
    """
    Return 200 only if the application can actually reach its database.

    Deliberately cheap: one round trip, no ORM, no model imports, so it stays
    fast enough to be polled every few minutes and cannot itself be the thing
    that falls over.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - any failure means "not healthy"
        logger.exception('Health check failed: database unreachable')
        return JsonResponse(
            {
                'status': 'unhealthy',
                'database': 'unreachable',
                'detail': f'{type(exc).__name__}: {exc}',
            },
            status=503,
        )

    return JsonResponse({'status': 'ok', 'database': 'ok'})
