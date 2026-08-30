from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import Profile
from draws.models import Draw, Winner
from draws.services.public_results import invalidate_public_draws_cache_on_commit


@receiver((post_save, post_delete), sender=Draw)
@receiver((post_save, post_delete), sender=Winner)
@receiver((post_save, post_delete), sender=Profile)
def invalidate_public_draws_cache(**kwargs):
    invalidate_public_draws_cache_on_commit()
