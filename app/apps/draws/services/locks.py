from django.db import connection


DRAW_LOCK_NAMESPACE = 7_312
DRAW_OPERATION_LOCK = 0


def lock_draw_operation(*, shared=False):
    function = (
        'pg_advisory_xact_lock_shared'
        if shared
        else 'pg_advisory_xact_lock'
    )
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT {function}(%s, %s)',
            [DRAW_LOCK_NAMESPACE, DRAW_OPERATION_LOCK],
        )
