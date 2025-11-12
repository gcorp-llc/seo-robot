TARGETS = [
    {
        "TARGET_DOMAIN": "gcorp.cc",
        "QUERIES": [
            "ویدا شکیبا"
        ],
        "SEARCH": False,
        "DIRECT_VISIT_URLS": [
            "https://gcorp.cc",
            "https://gcorp.cc/articles",
            "https://gcorp.cc/?page=2",
            "https://gcorp.cc/?page=3",
        ]
    },
]

def is_same_domain(url: str, target_domain: str) -> bool:
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc.lower().endswith(target_domain.lower())

def human_delay(min_delay: float, max_delay: float) -> float:
    import random
    return random.uniform(min_delay, max_delay)