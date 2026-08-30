from rest_framework.throttling import UserRateThrottle


class PromoCodeRegisterRateThrottle(UserRateThrottle):
    scope = 'promo_code_register'
