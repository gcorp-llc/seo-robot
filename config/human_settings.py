import os

HUMAN_DELAY_RANGE = (2.0, 4.5)
INTERACTION_DELAY_RANGE = (0.8, 2.0)
SCROLL_DELAY_RANGE = (3.0, 6.0)
BETWEEN_ENGINES_DELAY = (8, 15)
BETWEEN_PAGES_DELAY = (5, 10)
STAY_ON_PAGE_RANGE = (20, 40)

HUMAN_BEHAVIOR = {
    "typing_speed_range": (0.1, 0.3),
    "read_speed_wpm": (200, 300),
    "attention_span": (30, 90),
    "scroll_pattern": "natural",
}

MOUSE_MOVEMENTS_RANGE = (3, 7)
CLICK_CHANCE = 0.7
BACK_TO_TOP_CHANCE = 0.3
RANDOMNESS_FACTOR = float(os.getenv('RANDOMNESS_FACTOR', 0.3))