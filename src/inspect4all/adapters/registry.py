from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import ItemsView

    from inspect4all.core.interfaces import LanguageAdapter


class AdapterRegistry:
    """Lookup of language name -> adapter implementing LanguageAdapter.

    The single place a language becomes known to the pipeline; adapters
    self-describe via their `language_name` property.
    """

    def __init__(self, *adapters: LanguageAdapter):
        self._adapters: dict[str, LanguageAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: LanguageAdapter) -> None:
        self._adapters[adapter.language_name] = adapter

    def get(self, language: str) -> LanguageAdapter | None:
        return self._adapters.get(language)

    def items(self) -> ItemsView[str, LanguageAdapter]:
        return self._adapters.items()

    def supported_languages(self) -> list[str]:
        return list(self._adapters.keys())
