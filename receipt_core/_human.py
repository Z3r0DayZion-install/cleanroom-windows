"""Shared byte formatting for RECEIPT Core (internal)."""


def human_bytes(n):
    sign = '-' if n < 0 else ''
    n = abs(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{sign}{n:.1f}{unit}'
        n /= 1024
    return f'{sign}{n:.1f}PB'
