#!/usr/bin/env python3
import html
from typing import List, Optional, Callable, Dict
from .wofi_executor import WofiExecutor


class UIManager:
    """Generic UI manager for rofi interactions."""

    def __init__(self):
        self.wofi_executor = WofiExecutor()

    def _escape_markup(self, text: str) -> str:
        """Escape XML markup characters."""
        return html.escape(text)

    def show_menu(
        self, items: List[str], callbacks: Dict[str, Callable], prompt: str
    ) -> None:
        """Show menu using wofi directly."""
        selected = self.wofi_executor.call_wofi(items, prompt)
        
        if selected and selected in callbacks:
            try:
                callbacks[selected](selected)
            except Exception as e:
                print(f"Error executing callback: {e}")

    def select_item(self, items: List[str], prompt: str) -> Optional[str]:
        """Select single item from list and return it."""
        return self.wofi_executor.call_wofi(items, prompt)
