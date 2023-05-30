from typing import ClassVar
from textual.app import App, ComposeResult
from textual.scroll_view import ScrollView
from textual.reactive import reactive
from rich.cells import get_character_cell_size
from textual.strip import Strip
from textual import events
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.geometry import Size
from rich.segment import Segment
from typing import Iterator, Callable
from copy import deepcopy

UNKNOWN_CHARACTER = "_"

class PartialString():
    def __init__(self, length, replacement=UNKNOWN_CHARACTER) -> None:
        self.replacement = replacement
        self.length = length
        self._value = [None]*self.length

    def __eq__(self, other) -> bool:
        if not isinstance(other, PartialString):
            return False
        return other._value == self._value

    def __len__(self):
        return self.length

    def __getitem__(self, subscript):
        return self._value[subscript]

    def __setitem__(self, key, value):
        self._value[key] = value

    def __delitem__(self, key):
        self._value[key] = None

    def __iter__(self) -> Iterator[None | str]:
        return self._value.__iter__()

    def stringify(self, value, subst = None) -> str:
        if subst == None: subst = self.replacement
        return "".join([x if x else subst for x in value])

    def __repr__(self) -> str:
        return self.stringify(self._value)

    def split_lines(self, window_len = 80):
        max_line_length = window_len*2               
        result = []
        current = []
        for x in self._value:
            if x == "\n" or len(current) == max_line_length:
                result.append(current)
                current = []
            if x == "\n": continue
            current.append(x)
        return result

class TextArea(ScrollView, can_focus=True):
    DEFAULT_CSS = """
    TextArea {
        color: $accent;
        background: $surface;
        padding: 0;
        height: 100vh;
        max-width: 100vw;
        border: none;
    }
    TextArea > .textarea--cursor {
        background: $background;
        color: $text;
        text-style: reverse;
    }
    TextArea > .textarea--unknown {
        background: $surface !important;
        color: $primary;
    }
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "textarea--cursor", "textarea--unknown"}
    """
    | Class | Description |
    | :- | :- |
    | `textarea--cursor` | Target the cursor. |
    | `textarea--dunno` | Target the unknown characters. |
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "cursor_left", "cursor left", show=False),
        Binding("right", "cursor_right", "cursor right", show=False),
        Binding("up", "cursor_up", "cursor up", show=False),
        Binding("down", "cursor_down", "cursor down", show=False),
        Binding("backspace", "delete_left", "delete left", show=False),
        Binding("delete", "delete_right", "delete right", show=False),
    ]
    """
    | Key(s) | Description |
    | :- | :- |
    | left | Move the cursor left. |
    | right | Move the cursor right. |
    | up | Move the cursor up. |
    | down | Move the cursor down. |
    | backspace | Delete the character to the left of the cursor. |
    | delete | Delete the character to the right of the cursor. |
    """

    cursor_x = reactive(0)
    cursor_y = reactive(0)
    
    NUM_LINES = 3

    class Changed(Message):
        """Value changed message"""

        def __init__(self, previous: PartialString, current: PartialString) -> None:
            self.previous = previous
            self.current = current
            super().__init__()

    def __init__(self, text: str, value: PartialString, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.value = value

        self.lines = []
        
    def get_content_width(self, container, viewport):
        self.update_lines(min(container.width, viewport.width))
        super().get_content_width()

    def update_lines(self, window_len = 100):
        max_line_length = window_len*2               
        for x in self.text.splitlines():
            #if len(x) == 0: continue
            if len(x) >= max_line_length:
                self.lines.extend([x[i:i+max_line_length] for i in range(0, len(x), max_line_length)])
            else: 
                self.lines.append(x)
        
        self.virtual_size = Size(
            max([len(x) for x in self.lines]), len(self.lines) * self.NUM_LINES)

    async def _on_key(self, event: events.Key) -> None:
        self._cursor_visible = True
        # TODO: Blinking cursor

        # Handle key bindings
        if await self.handle_key(event):
            event.prevent_default()
            event.stop()
            return
        elif event.is_printable:
            event.stop()
            assert event.character is not None
            self.replace_char_at_cursor(event.character)
            self.cursor_x += 1
            event.prevent_default()

    def replace_char_at_cursor(self, char: str | None) -> None:
        """Insert char at the cursor, overriding other characters.

        Args:
            char: Text to insert.
        """
        start = sum([len(x)+1 for x in self.lines[:self.cursor_y]])
        prev = deepcopy(self.value)
        self.value[start+self.cursor_x] = char
        self.refresh()
        self.post_message(self.Changed(prev, self.value))

    def action_cursor_down(self) -> None:
        """Move the cursor one position downwards."""
        self.cursor_y += 1

    def action_cursor_up(self) -> None:
        """Move the cursor one position up."""
        self.cursor_y -= 1

    def action_cursor_left(self) -> None:
        """Move the cursor one position to the left."""
        self.cursor_x -= 1

    def action_cursor_right(self) -> None:
        """Move the cursor one position to the right."""
        self.cursor_x += 1

    def action_delete_left(self) -> None:
        """Delete character to the left"""
        self.cursor_x -= 1
        self.replace_char_at_cursor(None)

    def action_delete_right(self) -> None:
        """Delete character to the right"""
        self.cursor_x += 1
        self.replace_char_at_cursor(None)

    def validate_cursor_y(self, y):
        if y < 0:
            y = 0
        if y >= len(self.lines):
            y = len(self.lines)-1
        line = self.lines[y]
        if len(line) == 0:
            y += y-self.cursor_y # Skip two lines
        if self.cursor_x > len(line):
            self.cursor_x = len(line)-1
        return y

    def validate_cursor_x(self, x):
        def _line_length():
            return len(self.lines[self.cursor_y])
        
        if x < 0:
            old = self.cursor_y
            self.cursor_y -= 1
            if old == self.cursor_y:
                x = 0
            else:
                x = _line_length()-1

        if self.cursor_y+1 == len(self.lines):
            if x >= _line_length():
                x -= 1

        if x > _line_length()-1:
            x = 0
            self.cursor_y += 1
        return x
    
    @property
    def _cursor_point(self):
        return (self.cursor_x, self.cursor_y*self.NUM_LINES+1)

    def watch_cursor(self):
        scroll_x, scroll_y = self.scroll_offset
        
        x, y = self._cursor_point
        scroll_dx, scroll_dy = 0, 0
        if x >= scroll_x + self.size.width-2:
            scroll_dx = self.size.width//2
        if x <= scroll_x:
            scroll_dx = -scroll_x
            
        if y <= scroll_y or y >= scroll_y + self.size.height-2:
            scroll_dy = self.size.height//2
        if y <= scroll_y:
            scroll_dy *= -1
            
        self.scroll_to(scroll_x + scroll_dx, scroll_y + scroll_dy, animate=False)

    watch_cursor_x = watch_cursor
    watch_cursor_y = watch_cursor
    
    async def _on_click(self, event: events.Click) -> None:
        scroll_x, scroll_y = self.scroll_offset
        offset = event.get_content_offset(self)
        if offset is None:
            return
        event.stop()
        click_x = offset.x+scroll_x
        click_y = offset.y+scroll_y
        if click_y % self.NUM_LINES != 1:
            return
        else:
            self.cursor_y = click_y // self.NUM_LINES
        cell_offset = 0
        _cell_size = get_character_cell_size
        for index, char in enumerate(str(self.value)):
            if cell_offset >= click_x:
                self.cursor_x = index
                break
            cell_offset += _cell_size(char)
        else:
            self.cursor_x = self.value.length

    def on_resize(self, e: events.Resize):
        self.refresh(layout=True)
        self.update_lines(e.size.width)

    def render_line(self, y) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y
        alternate = y % self.NUM_LINES
        line_idx = y // self.NUM_LINES
        
        if line_idx >= len(self.lines):
            return Strip.blank(self.size.width)
        
        line = self.lines[line_idx]

        base_style = self.styles.rich_style
        unknown_style = self.get_component_rich_style("textarea--unknown")
        cursor_style = self.get_component_rich_style("textarea--cursor")

        if alternate == 0:
            strip = Strip([Segment(line), Segment(" "*(self.virtual_size.width-len(line)), base_style)])
        elif alternate == 1:
            start = sum([len(x)+1 for x in self.lines[:line_idx]])
            data_slice = self.value[start:start+len(line)+1]
            s = self.value.stringify(data_slice)
            segments = []
            for i, value in enumerate(data_slice):
                char = s[i]
                if char == "\n": continue
                if value == None:                    
                    segments.append(Segment(char, unknown_style))
                else:
                    segments.append(Segment(char, base_style))
                 
            if y == (self.cursor_y)*self.NUM_LINES+1:
                segments[self.cursor_x] = next(Segment.apply_style(Segment.strip_styles([segments[self.cursor_x]]),  cursor_style))
                    
            segments = Segment.simplify(segments)
            strip = Strip([
                *segments,
                Segment(
                    " "*(self.virtual_size.width-len(line)), base_style)
                ])
        else:
            strip = Strip.blank(self.virtual_size.width, base_style)
        
        return strip.crop(scroll_x, scroll_x + self.size.width)

class CribDragger(App):
    def __init__(self, text, on_change: Callable[[PartialString| None], PartialString] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.on_change = on_change

    def compose(self) -> ComposeResult:
        if self.on_change:
            value = self.on_change()
        else:
            value = PartialString(len(self.text)) 
        yield TextArea(self.text, value)

    def on_text_area_changed(self, e: TextArea.Changed):
        if self.on_change:
            self.query_one(TextArea).value = self.on_change(e.previous, e.current)

if __name__ == "__main__":
    CribDragger("""Test\nTest\nTEsst""").run()
