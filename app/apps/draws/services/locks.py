from django.db import connection


DRAW_LOCK_NAMESPACE = 7_312


def lock_draw_date(draw_date, *, shared=False):
    function = (
        'pg_advisory_xact_lock_shared'
        if shared
        else 'pg_advisory_xact_lock'
    )
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT {function}(%s, %s)',
            [DRAW_LOCK_NAMESPACE, draw_date.toordinal()],
        )
