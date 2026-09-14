from django.conf import settings


def request_ip(request):
    """Return the client address without trusting forwarded headers by default."""
    trusted_proxy_count = getattr(settings, 'TRUSTED_PROXY_COUNT', 0)
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    forwarded_addresses = [
        address.strip() for address in forwarded_for.split(',') if address.strip()
    ]
    if trusted_proxy_count > 0 and len(forwarded_addresses) >= trusted_proxy_count:
        return forwarded_addresses[-trusted_proxy_count]
    return request.META.get('REMOTE_ADDR', '')

