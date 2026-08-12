import secrets
from contextlib import contextmanager

from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from promo.models import PromoCode, PromoCodeGeneration


ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
CODE_LENGTH = 8
CODE_SPACE_SIZE = len(ALPHABET) ** CODE_LENGTH
BATCH_SIZE = 5_000
GENERATION_LOCK_ID = 7_304_219_871


def generate_random_code():
    number = secrets.randbelow(CODE_SPACE_SIZE)
    characters = ['0'] * CODE_LENGTH

    for index in range(CODE_LENGTH - 1, -1, -1):
        number, remainder = divmod(number, len(ALPHABET))
        characters[index] = ALPHABET[remainder]

    return ''.join(characters)


@contextmanager
def promo_code_generation_lock():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(%s)', [GENERATION_LOCK_ID])

    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s)', [GENERATION_LOCK_ID])


def generate_promo_codes(generation_id):
    generation = PromoCodeGeneration.objects.get(pk=generation_id)

    while generation.generated_count < generation.requested_count:
        remaining = generation.requested_count - generation.generated_count
        batch_size = min(BATCH_SIZE, remaining)
        candidates = _generate_unique_candidates(batch_size)
        inserted_count = _insert_candidates(candidates, generation.pk)
        generation.generated_count += inserted_count

    return generation.generated_count


def _generate_unique_candidates(count):
    candidates = set()
    while len(candidates) < count:
        candidates.add(generate_random_code())
    return candidates


def _insert_candidates(candidates, generation_id):
    table_name = connection.ops.quote_name(PromoCode._meta.db_table)
    placeholders = ', '.join(['(%s, %s)'] * len(candidates))
    created_at = timezone.now()
    parameters = []

    for code in candidates:
        parameters.extend((code, created_at))

    query = (
        f'INSERT INTO {table_name} ("code", "created_at") '
        f'VALUES {placeholders} '
        'ON CONFLICT ("code") DO NOTHING RETURNING "code"'
    )

    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(query, parameters)
        inserted_count = len(cursor.fetchall())
        PromoCodeGeneration.objects.filter(pk=generation_id).update(
            generated_count=F('generated_count') + inserted_count,
        )

    return inserted_count
