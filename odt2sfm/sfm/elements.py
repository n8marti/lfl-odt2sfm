import re


class SfmElement:
    """Text that begins with an SFM."""

    RE_SFM_INIT = re.compile(r"^\\[a-z]+[0-9]*( [0-9]+)* ")
    SFM_PLACEHOLDERS = {
        "~": "\u00a0",
    }

    def __init__(self, raw_text, odt_style=None):
        self._marker = None
        self._odt_style = odt_style
        self._sfm_raw = raw_text
        self._text = None

    @property
    def marker(self):
        if self._marker is None:
            match = self.RE_SFM_INIT.search(self.sfm_raw)
            if match is None:
                raise ValueError(f"No intial SFM marker: {self.sfm_raw}")
            self._marker = match[0].rstrip()
        return self._marker

    @property
    def odt_style(self):
        return self._odt_style

    @odt_style.setter
    def odt_style(self, value):
        self._odt_style = value

    @property
    def sfm_raw(self):
        return self._sfm_raw

    # @sfm_raw.setter
    # def sfm_raw(self, value):
    #     if not value.startswith("\\"):
    #         raise ValueError("SFM text does not begin with a backslash '\\'")
    #     self._sfm_raw = value

    @property
    def text(self):
        if self._text is None:
            # Remove leading SFM marker.
            text = self.sfm_raw.removeprefix(f"{self.marker} ")
            sanitized_text = self._sanitize(text)
            self._text = sanitized_text
        return self._text

    @classmethod
    def _sanitize(cls, text):
        sanitized_text = ""
        for c in text:
            sanitized_text += cls.SFM_PLACEHOLDERS.get(c, c)
        return sanitized_text

    def __str__(self):
        return self.sfm_raw


class SfmSpan(SfmElement):
    """Text that has additional, character-level formatting added.
    It must close with another SFM marker that matches the first one, unless
    it's a verse number reference."""

    RE_SFM_END = re.compile(r"\\[a-z]+\*$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._end_marker = None
        if self.end_marker and self.marker != self.end_marker.rstrip("*"):
            raise ValueError(f"Unmatched markers: {self.marker} & {self.end_marker}")

    @property
    def end_marker(self):
        if self._end_marker is None:
            if self.sfm_raw.startswith("\\v"):  # special handling for verses
                return self._end_marker
            match = self.RE_SFM_END.search(self.sfm_raw)
            if match is None:
                raise ValueError(f"No intial SFM marker: {self.sfm_raw}")
            self._end_marker = match[0].rstrip()
        return self._end_marker

    @property
    def text(self):
        if self._text is None:
            # Initialize and remove leading SFM marker.
            text = super().text
            # Check for trailing SFM marker.
            if self.end_marker and self.end_marker.rstrip("*") == self.marker:
                # Remove "closing" marker.
                text = text.removesuffix(self.end_marker)
            self._text = self._sanitize(text)
        return self._text


class SfmParagraph(SfmElement):
    """Paragraphs can be composed of multiple text lines if containing one or
    more verses. They can contain zero or more spans."""

    # RE_SFM_OPEN = re.compile(r"\\[a-z]+ ")

    @property
    def spans(self):
        # FIXME: Tricky situation. We're assuming all opening markers are
        # followed by corresponding closing markers; i.e. there are no nested
        # spans.
        spans = []
        parts = self.sfm_raw.split("\\")
        last_part_init = None
        last_part_text = None
        for part in parts:
            if len(part) == 0:  # ignore empty split
                continue
            # FIXME: Again, we're making a big assumption that any "* " is
            # always the end of a span-closing marker.
            part_init, s, part_text = re.split(r"( |\*)", part, maxsplit=1)
            if part_init == "v":  # verses are special kinds of spans
                v_num = part_text.split(" ", maxsplit=1)[0]
                sfm_raw = f"\\v {v_num}"
                part_text = v_num
                spans.append(SfmSpan(sfm_raw))
            elif s == "*" and part_init == last_part_init:
                sfm_raw = f"\\{last_part_init} {last_part_text}\\{part_init}{s}"
                spans.append(SfmSpan(sfm_raw))
            last_part_init = part_init
            last_part_text = part_text
        return spans

    @property
    def text(self):
        if self._text is None:
            # Initialize and remove leading SFM marker.
            text = super().text
            # TODO: Remove any verse or span SFM markers?
            # text = self._text
            self._text = self._sanitize(text)
        return self._text

    @property
    def texts(self):
        texts = []
        if self.spans:  # texts are only relevant if there are spans
            if self.marker[1] == "v":  # don't remove verse marker if present
                text_init = self.sfm_raw
            else:
                text_init = self.sfm_raw.removeprefix(self.marker)
            remainder = text_init
            for s in self.spans:
                t, remainder = remainder.split(s.sfm_raw, maxsplit=1)
                if t and t.replace(" ", "") != "":
                    texts.append(self._sanitize(t))
            if remainder != text_init:
                texts.append(self._sanitize(remainder))
        return texts
