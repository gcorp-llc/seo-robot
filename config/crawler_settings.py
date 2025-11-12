MODES = {
    "deep_crawl": True,
}

DEEP_CRAWL_MAX_LINKS = 5
DEEP_CRAWL_MAX_DEPTH = 2

def get_deep_crawl_selectors(target_domain: str) -> list:
    if not target_domain:
        return []
    return [
        f'a[href*="{target_domain}"]',
        'article a[href^="/"]',
        'nav a[href^="/"]',
        'main a[href^="/"]',
        'div.content a[href^="/"]',
        'a.internal-link',
        'a[href^="/"]:not([href^="//"])',
    ]

FALLBACK_STRATEGIES = {
    "extract_from_text": True,
    "use_navigation_timing": True,
    "check_redirects": True,
    "parse_json_ld": True,
    "extract_from_meta": True,
    "use_regex_patterns": True,
    "extract_from_scripts": True,
    "try_alternative_selectors": True,
    "use_aria_labels": True,
    "extract_from_images": True
}

MAX_SCROLL_ROUNDS = 5
PAGE_SCROLL_PASSES = 8
MAX_RESULTS_TO_CHECK = 30  # اضافه شده برای حل ImportError