import sublime
import re
from sublime import Settings


class CodeGetter:

    def __init__(self, view):
        self.view = view
        self.settings = Settings(view)
        self.auto_expand_line = True
        self.auto_advance = True
        self.auto_advance_non_empty = False

    @classmethod
    def initialize(cls, view):
        return CodeGetter(view)

    def expand_cursor(self, s):
        s = self.view.line(s)
        if self.auto_expand_line:
            s = self.expand_line(s)
        return s

    def expand_line(self, s):
        return s

    def substr(self, s):
        return self.view.substr(s)

    def advance(self, s):
        view = self.view
        pt = view.text_point(view.rowcol(s.end())[0] + 1, 0)
        if self.auto_advance_non_empty:
            nextpt = view.find(r"\S", pt)
            if nextpt.begin() != -1:
                pt = view.text_point(view.rowcol(nextpt.begin())[0], 0)
        view.sel().add(sublime.Region(pt, pt))

    def get_text(self):
        view = self.view
        cmd = ''
        moved = False
        sels = [s for s in view.sel()]
        for s in sels:
            if s.empty():
                original_s = s
                s = self.expand_cursor(s)
                if self.auto_advance:
                    view.sel().subtract(original_s)
                    self.advance(s)
                    moved = True

            cmd += self.substr(s) + '\n'

        if moved:
            view.show(view.sel())

        return cmd
