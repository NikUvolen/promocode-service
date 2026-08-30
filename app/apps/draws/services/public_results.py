from django.core.cache import cache
from django.db import transaction


PUBLIC_DRAWS_CACHE_KEY = 'public-draws:v1'


def invalidate_public_draws_cache():
    cache.delete(PUBLIC_DRAWS_CACHE_KEY)


def invalidate_public_draws_cache_on_commit():
    transaction.on_commit(invalidate_public_draws_cache)
