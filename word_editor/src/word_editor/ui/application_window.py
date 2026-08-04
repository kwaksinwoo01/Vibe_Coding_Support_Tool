from __future__ import annotations

from typing import Any

from word_editor.ui.main_window import MainWindow
from word_editor.ui.style_visibility import belongs_to_hidden_tab


class ApplicationMainWindow(MainWindow):
    """Main window with the repository's active/hidden tab policy."""

    @staticmethod
    def _is_hidden_style(style: Any) -> bool:
        return belongs_to_hidden_tab(style)
