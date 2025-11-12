import random
from urllib.parse import urlparse, urljoin, quote_plus
from typing import List

from config.human_settings import RANDOMNESS_FACTOR, HUMAN_DELAY_RANGE

def human_delay(a: float = None, b: float = None, randomness: float = RANDOMNESS_FACTOR) -> float:
    if a is None or b is None:
        a, b = HUMAN_DELAY_RANGE
    base_delay = random.uniform(a, b)
    variance = base_delay * randomness * random.uniform(-1, 1)
    return max(0.5, base_delay + variance)

def is_same_domain(url: str, domain: str) -> bool:
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        target = domain.lower().replace("www.", "")
        return netloc == target or netloc.endswith(f".{target}")
    except Exception:
        return False

def is_valid_url(url: str, exclude_domains: List[str] = None) -> bool:
    if not url or not url.startswith("http"):
        return False
    if exclude_domains:
        for domain in exclude_domains:
            if domain in url.lower():
                return False
    return True