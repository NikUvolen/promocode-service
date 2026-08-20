from math import ceil

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as drf_exception_handler


def _format_wait_time(seconds):
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    parts = []

    if hours:
        parts.append(f'{hours} ч.')
    if minutes:
        parts.append(f'{minutes} мин.')
    if seconds or not parts:
        parts.append(f'{seconds} сек.')

    return ' '.join(parts)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(exc, Throttled):
        return response

    retry_after = max(1, ceil(exc.wait or 1))
    response.data = {
        'detail': (
            'Слишком много запросов. Повторите попытку через '
            f'{_format_wait_time(retry_after)}'
        ),
        'retry_after': retry_after,
    }
    return response
