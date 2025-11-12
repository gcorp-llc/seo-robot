TARGETS = [
    {
        "TARGET_DOMAIN": "drshakibavida.com",
        "QUERIES": [
            "بهترین دکتر برای تزریق ژل در زعفرانیه",
            "بهترین دکتر برای تزریق بوتاکس در زعفرانیه",
        ],
        "SEARCH": True,
        "DIRECT_VISIT_URLS": [
            "https://drshakibavida.com/%d9%85%d9%82%d8%a7%d9%84%d8%a7%d8%aa/",
            "https://drshakibavida.com/%d8%a8%d9%87%d8%aa%d8%b1%db%8c%d9%86-%d8%af%da%a9%d8%aa%d8%b1-%d8%a8%d8%b1%d8%a7%db%8c-%d8%aa%d8%b2%d8%b1%db%8c%d9%82-%d8%a8%d9%88%d8%aa%d8%a7%da%a9%d8%b3-%d8%af%d8%b1-%d8%b2%d8%b9%d9%81%d8%b1%d8%a7/",
            "https://drshakibavida.com/%d8%aa%d8%ad%d9%84%db%8c%d9%84-%d9%85%d9%82%d8%a7%db%8c%d8%b3%d9%87%d8%a7%db%8c-%d8%aa%d8%b2%d8%b1%db%8c%d9%82-%da%98%d9%84-%d9%81%db%8c%d9%84%d8%b1-%d9%88-%d9%85%d8%b2%d9%88%da%98%d9%84/",
            "https://drshakibavida.com/%d8%b2%db%8c%d8%a8%d8%a7%db%8c%db%8c-%d9%86%da%86%d8%b1%d8%a7%d9%84-natural-beauty-%d8%b1%d8%a7%d9%87%d9%86%d9%85%d8%a7%db%8c-%d8%af%d8%b3%d8%aa%db%8c%d8%a7%d8%a8%db%8c-%d8%a8%d9%87-%d9%86%d8%aa/",
            "https://drshakibavida.com/%d8%b1%d8%a7%d8%b2-%d9%84%db%8c%d9%81%d8%aa-%d8%b5%d9%88%d8%b1%d8%aa-%d8%a8%d8%af%d9%88%d9%86-%d8%ac%d8%b1%d8%a7%d8%ad%db%8c-%d8%a8%d8%a7-md-codes-%d8%af%d8%b1-%d9%88%d9%84%d9%86%d8%ac%da%a9-%d9%86/",
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