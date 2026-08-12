from django.db import transaction

from accounts.models import Profile


@transaction.atomic
def update_profile(
    *,
    profile: Profile,
    first_name: str,
    last_name: str,
    middle_name: str,
    no_middle_name: bool,
    phone: str,
) -> Profile:
    profile.first_name = first_name
    profile.last_name = last_name
    profile.middle_name = '' if no_middle_name else middle_name
    profile.no_middle_name = no_middle_name
    profile.phone = phone
    profile.save(
        update_fields=(
            'first_name',
            'last_name',
            'middle_name',
            'no_middle_name',
            'phone',
            'updated_at',
        )
    )
    return profile
