from .behavior import random_interactions, human_reading_behavior
from .captcha import handle_captcha
from .actions import (
    scroll_page_naturally,
    move_mouse_bezier,
    random_page_interactions,
    handle_common_popups
)

__all__ = [
    "random_interactions",
    "human_reading_behavior",
    "handle_captcha",
    "scroll_page_naturally",
    "move_mouse_bezier",
    "random_page_interactions",
    "handle_common_popups"
]
