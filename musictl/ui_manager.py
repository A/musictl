#!/usr/bin/env python3
import html
from typing import List, Optional, Callable, Dict

from pyrofi import run_menu, WOFI_CMD


class UIManager:
    """Generic UI manager for rofi interactions."""

    def _escape_markup(self, text: str) -> str:
        """Escape XML markup characters."""
        return html.escape(text)

    def show_menu(
        self, items: List[str], callbacks: Dict[str, Callable], prompt: str
    ) -> None:
        """Show menu using rofi."""
        escaped_menu = {}
        for item in items:
            escaped_item = self._escape_markup(item)  # Removed .lower()
            callback = callbacks.get(item, lambda _: None)
            escaped_menu[escaped_item] = callback

        try:
            run_menu(
                escaped_menu,
                prefix=prompt,
                menu_cmd=WOFI_CMD,
            )
        except Exception:
            pass

    def select_item(self, items: List[str], prompt: str) -> Optional[str]:
        """Select single item from list and return it."""
        selected = None

        def make_selector(original_item):
            def selector(_):
                nonlocal selected
                selected = original_item  # Return original unescaped item
                return False

            return selector

        escaped_menu = {}
        for item in items:
            escaped_item = self._escape_markup(item)  # Removed .lower()
            escaped_menu[escaped_item] = make_selector(item)

        try:
            run_menu(
                escaped_menu,
                prefix=prompt,
                menu_cmd=WOFI_CMD,
            )
        except Exception:
            pass

        return selected
