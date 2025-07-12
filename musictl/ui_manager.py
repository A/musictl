#!/usr/bin/env python3
from typing import List, Optional, Callable, Dict

from pyrofi import run_menu, WOFI_CMD


class UIManager:
    """Generic UI manager for rofi interactions."""

    def show_menu(
        self, items: List[str], callbacks: Dict[str, Callable], prompt: str
    ) -> None:
        """Show menu using rofi."""
        menu = {item: callbacks.get(item, lambda _: None) for item in items}

        try:
            run_menu(menu, prompt=prompt, menu_cmd=WOFI_CMD)
        except Exception:
            pass

    def select_item(self, items: List[str], prompt: str) -> Optional[str]:
        """Select single item from list and return it."""
        selected = None

        def make_selector(item):
            def selector(_):
                nonlocal selected
                selected = item
                return False

            return selector

        callbacks = {item: make_selector(item) for item in items}
        self.show_menu(items, callbacks, prompt)
        return selected
