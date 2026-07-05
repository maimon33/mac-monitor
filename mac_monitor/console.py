from __future__ import annotations

import sys


ALT_SCREEN_ON = "\033[?1049h"
ALT_SCREEN_OFF = "\033[?1049l"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"
CURSOR_HOME = "\033[H"
ERASE_SCREEN = "\033[2J"
ERASE_TO_END = "\033[J"


class TerminalScreen:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._active = False

    def __enter__(self) -> "TerminalScreen":
        if self.enabled:
            sys.stdout.write(ALT_SCREEN_ON + CURSOR_HIDE + ERASE_SCREEN + CURSOR_HOME)
            sys.stdout.flush()
            self._active = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._active:
            sys.stdout.write(CURSOR_SHOW + ALT_SCREEN_OFF)
            sys.stdout.flush()
            self._active = False

    def frame_prefix(self) -> str:
        if not self.enabled:
            return ""
        return CURSOR_HOME + ERASE_TO_END
