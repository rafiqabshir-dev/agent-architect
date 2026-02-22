_JSON_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
}


class RawJsonStreamParser:
    """Parses raw partial_json fragments from input_json_delta events.

    Expects the tool input JSON shape: {"requirements": "...", "design": "...", "tasks": "..."}
    Uses a state machine to track which field value is being written and yields
    unescaped string content character-by-character as deltas.
    """

    FIELDS = frozenset(("requirements", "design", "tasks"))

    def __init__(self):
        self._state = "EXPECT_KEY"
        self._key_buf: list[str] = []
        self._current_field: str | None = None
        self._escape = False

    def feed(self, partial_json: str) -> list[tuple[str, str]]:
        """Feed a partial_json fragment. Returns [(field, text_delta), ...]"""
        deltas = []
        delta_buf: list[str] = []

        for ch in partial_json:
            # Handle escape sequences inside strings
            if self._escape:
                self._escape = False
                if self._state == "IN_VALUE" and self._current_field:
                    delta_buf.append(_JSON_ESCAPES.get(ch, ch))
                elif self._state == "IN_KEY":
                    self._key_buf.append(ch)
                continue

            if ch == "\\" and self._state in ("IN_KEY", "IN_VALUE"):
                self._escape = True
                continue

            if self._state == "EXPECT_KEY":
                if ch == '"':
                    self._state = "IN_KEY"
                    self._key_buf = []
                # skip whitespace, {, etc.

            elif self._state == "IN_KEY":
                if ch == '"':
                    key = "".join(self._key_buf)
                    self._current_field = key if key in self.FIELDS else None
                    self._state = "EXPECT_COLON"
                else:
                    self._key_buf.append(ch)

            elif self._state == "EXPECT_COLON":
                if ch == ":":
                    self._state = "EXPECT_VALUE"

            elif self._state == "EXPECT_VALUE":
                if ch == '"':
                    self._state = "IN_VALUE"

            elif self._state == "IN_VALUE":
                if ch == '"':
                    # End of value — flush any buffered delta
                    if delta_buf and self._current_field:
                        deltas.append((self._current_field, "".join(delta_buf)))
                        delta_buf = []
                    self._current_field = None
                    self._state = "EXPECT_COMMA_OR_END"
                else:
                    if self._current_field:
                        delta_buf.append(ch)

            elif self._state == "EXPECT_COMMA_OR_END":
                if ch == ",":
                    self._state = "EXPECT_KEY"
                # skip } and whitespace

        # Flush remaining buffered delta (partial string still being written)
        if delta_buf and self._current_field:
            deltas.append((self._current_field, "".join(delta_buf)))

        return deltas
