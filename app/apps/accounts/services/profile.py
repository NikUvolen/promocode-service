from django.db import transaction

from accounts.models import Profile


def normalize_phone(phone: str) -> str:
    digits = ''.join(character for character in phone if character.isdigit())
    if len(digits) == 10:
        digits = f'7{digits}'
    elif len(digits) == 11 and digits.startswith('8'):
        digits = f'7{digits[1:]}'

    if len(digits) != 11 or not digits.startswith('7'):
        raise ValueError('Invalid Russian phone number')

    return (
        f'+7 ({digits[1:4]}) {digits[4:7]}-'
        f'{digits[7:9]}-{digits[9:11]}'
    )


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
