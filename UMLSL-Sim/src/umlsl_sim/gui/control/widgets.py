"""A small immediate-need widget toolkit for the control GUI.

pyglet ships only very primitive GUI helpers, so this module implements the few
widgets the control panel needs (button, dropdown, checkbox, single-line text
field, log view) on top of ``pyglet.shapes`` and ``pyglet.text``.

Coordinates follow pyglet's convention: origin bottom-left, ``y`` increasing
upwards. Every widget stores its **bottom-left** corner in ``x``/``y`` and its
size in ``w``/``h``. Widgets keep persistent shape objects and only mutate their
colour / text / position on state changes, so drawing is just ``batch.draw()``.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence

import pyglet
from pyglet import shapes
from pyglet.text import Label

from umlsl_sim.gui.control import theme


class Widget:
    """Base class: a rectangular, optionally interactive control."""

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.visible = True
        self.enabled = True
        self._objects: List = []

    # --- geometry ---------------------------------------------------------
    def contains(self, px: float, py: float) -> bool:
        return self.visible and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    # --- lifecycle --------------------------------------------------------
    def _track(self, obj):
        self._objects.append(obj)
        return obj

    def delete(self) -> None:
        for obj in self._objects:
            try:
                obj.delete()
            except Exception:
                pass
        self._objects.clear()

    def set_visible(self, value: bool) -> None:
        self.visible = value
        for obj in self._objects:
            obj.visible = value

    def set_enabled(self, value: bool) -> None:
        self.enabled = value
        self._refresh()

    # --- overridable hooks ------------------------------------------------
    def _refresh(self) -> None:  # update colours/text after a state change
        pass

    # --- event hooks (return True if the event was consumed) -------------
    def on_mouse_motion(self, x, y) -> bool:
        return False

    def on_mouse_press(self, x, y, button) -> bool:
        return False

    def on_mouse_release(self, x, y, button) -> bool:
        return False


class Button(Widget):
    KIND_DEFAULT = "default"
    KIND_PRIMARY = "primary"
    KIND_DANGER = "danger"

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        on_click: Callable[[], None],
        batch,
        group,
        kind: str = KIND_DEFAULT,
        font_size: int = theme.FONT_SIZE,
    ) -> None:
        super().__init__(x, y, w, h)
        self.text = text
        self.on_click = on_click
        self.kind = kind
        self._hover = False
        self._pressed = False

        self._bg = self._track(
            shapes.Rectangle(x, y, w, h, color=self._base_color(), batch=batch, group=group)
        )
        self._label = self._track(
            Label(
                text,
                font_name=theme.FONT,
                font_size=font_size,
                weight="bold",
                color=(*theme.TEXT, 255),
                x=x + w / 2,
                y=y + h / 2,
                anchor_x="center",
                anchor_y="center",
                batch=batch,
                group=group,
            )
        )
        self._refresh()

    def _base_color(self):
        return {
            self.KIND_PRIMARY: theme.GREEN,
            self.KIND_DANGER: theme.RED,
            self.KIND_DEFAULT: theme.LAYER,
        }[self.kind]

    def _hover_color(self):
        return {
            self.KIND_PRIMARY: theme.GREEN_HOVER,
            self.KIND_DANGER: theme.RED_HOVER,
            self.KIND_DEFAULT: theme.LAYER_HOVER,
        }[self.kind]

    def set_text(self, text: str) -> None:
        self.text = text
        self._label.text = text

    def _refresh(self) -> None:
        if not self.enabled:
            self._bg.color = theme.PANEL
            self._label.color = (*theme.DISABLED_TEXT, 255)
            return
        if self._pressed:
            self._bg.color = theme.darken(self._base_color(), 0.15)
        elif self._hover:
            self._bg.color = self._hover_color()
        else:
            self._bg.color = self._base_color()
        self._label.color = (*theme.TEXT, 255)

    def on_mouse_motion(self, x, y) -> bool:
        inside = self.contains(x, y)
        if inside != self._hover:
            self._hover = inside
            self._refresh()
        return inside

    def on_mouse_press(self, x, y, button) -> bool:
        if self.enabled and self.contains(x, y):
            self._pressed = True
            self._refresh()
            return True
        return False

    def on_mouse_release(self, x, y, button) -> bool:
        was_pressed = self._pressed
        self._pressed = False
        self._refresh()
        if was_pressed and self.enabled and self.contains(x, y):
            self.on_click()
            return True
        return False


class Dropdown(Widget):
    """A select control. The open menu is drawn via ``overlay_group`` so it sits
    above sibling widgets. Only one dropdown should be open at a time; the owning
    app coordinates that through :meth:`open` / :meth:`close`."""

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        options: Sequence[str],
        on_change: Callable[[str], None],
        batch,
        group,
        overlay_group,
        selected: Optional[str] = None,
    ) -> None:
        super().__init__(x, y, w, h)
        self._batch = batch
        self._overlay_group = overlay_group
        self.options = list(options)
        self.on_change = on_change
        self.selected = selected if selected is not None else (self.options[0] if self.options else "")
        self.is_open = False
        self._hover = False
        self._menu_objs: List = []
        self._hover_index = -1

        self._bg = self._track(
            shapes.Rectangle(x, y, w, h, color=theme.LAYER, batch=batch, group=group)
        )
        self._label = self._track(
            Label(
                self._display_text(),
                font_name=theme.FONT,
                font_size=theme.FONT_SIZE,
                color=(*theme.TEXT, 255),
                x=x + 10,
                y=y + h / 2,
                anchor_x="left",
                anchor_y="center",
                batch=batch,
                group=group,
            )
        )
        # caret triangle
        cx = x + w - 16
        cy = y + h / 2
        self._arrow = self._track(
            shapes.Triangle(
                cx - 5, cy + 3, cx + 5, cy + 3, cx, cy - 4,
                color=theme.MUTED_TEXT, batch=batch, group=group,
            )
        )
        self._refresh()

    def _display_text(self) -> str:
        return self.selected if self.selected else "—"

    def set_options(self, options: Sequence[str], selected: Optional[str] = None) -> None:
        self.options = list(options)
        if selected is not None:
            self.selected = selected
        elif self.selected not in self.options:
            self.selected = self.options[0] if self.options else ""
        self._label.text = self._display_text()

    def set_selected(self, value: str, fire: bool = False) -> None:
        self.selected = value
        self._label.text = self._display_text()
        if fire:
            self.on_change(value)

    def _refresh(self) -> None:
        if not self.enabled:
            self._bg.color = theme.PANEL
            self._label.color = (*theme.DISABLED_TEXT, 255)
            self._arrow.color = theme.DISABLED_TEXT
            return
        self._bg.color = theme.LAYER_HOVER if (self._hover or self.is_open) else theme.LAYER
        self._label.color = (*theme.TEXT, 255)
        self._arrow.color = theme.MUTED_TEXT

    # --- open / close -----------------------------------------------------
    def _row_height(self) -> float:
        return self.h

    def open(self) -> None:
        if self.is_open or not self.options:
            return
        self.is_open = True
        self._refresh()
        rh = self._row_height()
        n = len(self.options)
        top = self.y  # menu drops downwards from the widget's bottom edge
        for i, opt in enumerate(self.options):
            ry = top - (i + 1) * rh
            rect = shapes.Rectangle(
                self.x, ry, self.w, rh,
                color=theme.LAYER_ACTIVE if opt == self.selected else theme.LAYER,
                batch=self._batch, group=self._overlay_group,
            )
            lbl = Label(
                opt,
                font_name=theme.FONT,
                font_size=theme.FONT_SIZE,
                color=(*theme.TEXT, 255),
                x=self.x + 10,
                y=ry + rh / 2,
                anchor_x="left",
                anchor_y="center",
                batch=self._batch,
                group=self._overlay_group,
            )
            self._menu_objs.append((rect, lbl))

    def close(self) -> None:
        if not self.is_open:
            return
        self.is_open = False
        self._hover_index = -1
        for rect, lbl in self._menu_objs:
            rect.delete()
            lbl.delete()
        self._menu_objs.clear()
        self._refresh()

    def _menu_index_at(self, x, y) -> int:
        if not self.is_open:
            return -1
        rh = self._row_height()
        for i in range(len(self.options)):
            ry = self.y - (i + 1) * rh
            if self.x <= x <= self.x + self.w and ry <= y <= ry + rh:
                return i
        return -1

    def menu_contains(self, x, y) -> bool:
        return self._menu_index_at(x, y) != -1

    def on_mouse_motion(self, x, y) -> bool:
        inside = self.contains(x, y)
        if inside != self._hover:
            self._hover = inside
            self._refresh()
        if self.is_open:
            idx = self._menu_index_at(x, y)
            if idx != self._hover_index:
                self._hover_index = idx
                for i, (rect, _lbl) in enumerate(self._menu_objs):
                    if self.options[i] == self.selected:
                        rect.color = theme.LAYER_ACTIVE
                    else:
                        rect.color = theme.LAYER_HOVER if i == idx else theme.LAYER
            return True
        return inside

    def on_mouse_press(self, x, y, button) -> bool:
        # Consumed by the app's global handling; see app.py. Kept for symmetry.
        return self.contains(x, y) or self.menu_contains(x, y)

    def choose_at(self, x, y) -> bool:
        idx = self._menu_index_at(x, y)
        if idx >= 0:
            value = self.options[idx]
            changed = value != self.selected
            self.close()
            self.set_selected(value)
            if changed:
                self.on_change(value)
            return True
        return False


class Checkbox(Widget):
    def __init__(
        self,
        x: float,
        y: float,
        size: float,
        text: str,
        checked: bool,
        on_change: Callable[[bool], None],
        batch,
        group,
    ) -> None:
        # widget height matches the box; width extends over the label for hit-testing
        super().__init__(x, y, 240, size)
        self.box_size = size
        self.checked = checked
        self.on_change = on_change
        self._hover = False

        self._box = self._track(
            shapes.Rectangle(x, y, size, size, color=theme.LAYER, batch=batch, group=group)
        )
        self._check = self._track(
            shapes.Rectangle(
                x + size * 0.25, y + size * 0.25, size * 0.5, size * 0.5,
                color=theme.GREEN, batch=batch, group=group,
            )
        )
        self._label = self._track(
            Label(
                text,
                font_name=theme.FONT,
                font_size=theme.FONT_SIZE,
                color=(*theme.TEXT, 255),
                x=x + size + 10,
                y=y + size / 2,
                anchor_x="left",
                anchor_y="center",
                batch=batch,
                group=group,
            )
        )
        self._refresh()

    def set_checked(self, value: bool) -> None:
        self.checked = value
        self._refresh()

    def _refresh(self) -> None:
        self._check.visible = self.visible and self.checked
        if not self.enabled:
            self._box.color = theme.PANEL
            self._label.color = (*theme.DISABLED_TEXT, 255)
            return
        self._box.color = theme.LAYER_HOVER if self._hover else theme.LAYER
        self._label.color = (*theme.TEXT, 255)

    def set_visible(self, value: bool) -> None:
        super().set_visible(value)
        # keep the tick hidden when unchecked even if the widget is shown
        self._check.visible = value and self.checked

    def on_mouse_motion(self, x, y) -> bool:
        inside = self.contains(x, y)
        if inside != self._hover:
            self._hover = inside
            self._refresh()
        return inside

    def on_mouse_press(self, x, y, button) -> bool:
        if self.enabled and self.contains(x, y):
            self.checked = not self.checked
            self._refresh()
            self.on_change(self.checked)
            return True
        return False


class TextField(Widget):
    """Single-line editable field with app-managed focus."""

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        value: str,
        batch,
        group,
        on_change: Optional[Callable[[str], None]] = None,
        placeholder: str = "",
        allowed: Optional[str] = None,
        max_len: int = 40,
    ) -> None:
        super().__init__(x, y, w, h)
        self.value = value
        self.placeholder = placeholder
        self.on_change = on_change
        self.allowed = allowed  # if set, only these characters are accepted
        self.max_len = max_len
        self.focused = False

        self._bg = self._track(
            shapes.Rectangle(x, y, w, h, color=theme.LAYER, batch=batch, group=group)
        )
        self._border = self._track(
            shapes.Rectangle(x, y, w, 2, color=theme.LAYER, batch=batch, group=group)
        )
        self._label = self._track(
            Label(
                self._display(),
                font_name=theme.FONT,
                font_size=theme.FONT_SIZE,
                color=self._text_color(),
                x=x + 8,
                y=y + h / 2,
                anchor_x="left",
                anchor_y="center",
                batch=batch,
                group=group,
            )
        )
        self._caret = self._track(
            shapes.Rectangle(x + 8, y + 6, 1.5, h - 12, color=theme.TEXT, batch=batch, group=group)
        )
        self._caret.visible = False
        self._refresh()

    def _display(self) -> str:
        return self.value if self.value else self.placeholder

    def _text_color(self):
        return (*theme.TEXT, 255) if self.value else (*theme.MUTED_TEXT, 255)

    def set_value(self, value: str) -> None:
        self.value = value
        self._label.text = self._display()
        self._label.color = self._text_color()
        self._update_caret()

    def _update_caret(self) -> None:
        self._caret.x = self._label.x + self._label.content_width + 2
        self._caret.visible = self.visible and self.focused

    def _refresh(self) -> None:
        self._border.color = theme.GREEN if self.focused else theme.BORDER
        self._label.color = self._text_color()
        self._update_caret()

    def set_visible(self, value: bool) -> None:
        super().set_visible(value)
        self._caret.visible = value and self.focused

    def set_focus(self, value: bool) -> None:
        self.focused = value
        self._refresh()

    def on_mouse_press(self, x, y, button) -> bool:
        return self.enabled and self.contains(x, y)

    # text editing (driven by the app while focused)
    def insert(self, text: str) -> None:
        for ch in text:
            if self.allowed is not None and ch not in self.allowed:
                continue
            if len(self.value) >= self.max_len:
                break
            self.value += ch
        self.set_value(self.value)
        if self.on_change:
            self.on_change(self.value)

    def backspace(self) -> None:
        if self.value:
            self.value = self.value[:-1]
            self.set_value(self.value)
            if self.on_change:
                self.on_change(self.value)


class LogView(Widget):
    """A read-only text panel that shows the tail of a message log."""

    def __init__(self, x, y, w, h, batch, group, title: str = "Status") -> None:
        super().__init__(x, y, w, h)
        self.lines: List[str] = []
        self._bg = self._track(
            shapes.Rectangle(x, y, w, h, color=theme.PANEL, batch=batch, group=group)
        )
        self._title = self._track(
            Label(
                title,
                font_name=theme.FONT,
                font_size=theme.FONT_SIZE_SMALL,
                weight="bold",
                color=(*theme.MUTED_TEXT, 255),
                x=x + 10,
                y=y + h - 8,
                anchor_x="left",
                anchor_y="top",
                batch=batch,
                group=group,
            )
        )
        self._doc = self._track(
            Label(
                "",
                font_name="Consolas",
                font_size=theme.FONT_SIZE_SMALL,
                color=(*theme.TEXT, 255),
                x=x + 10,
                y=y + h - 26,
                width=w - 20,
                multiline=True,
                anchor_x="left",
                anchor_y="top",
                batch=batch,
                group=group,
            )
        )
        self._max_lines = max(1, int((h - 34) / 15))

    def append(self, text: str) -> None:
        for line in str(text).splitlines() or [""]:
            self.lines.append(line)
        self.lines = self.lines[-200:]
        self._doc.text = "\n".join(self.lines[-self._max_lines:])
