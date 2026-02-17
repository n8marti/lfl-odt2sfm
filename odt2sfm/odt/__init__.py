import re
from pathlib import Path

from odf.element import Node
from odf.namespaces import TEXTNS
from odf.opendocument import load
from odf.teletype import extractText

from .elements import OdtParagraph


class OdtChapter:
    """One "lesson" ODT file in "Lessons from Luke", which corresponds to a
    "chapter" in Paratext."""

    RE_2_DIGITS = re.compile(r"(?<=L)[0-9]{2}")

    def __init__(self, file_path=None):
        if file_path is None:
            raise ValueError("No file path was given for this lesson.")
        else:
            self.file_path = Path(file_path)
        if not self.file_path.is_file():
            raise ValueError(f"File does not exist: {self.file_path}")

        self._odt = None
        self._sfm_ref = None
        self._all_styles = None
        self._styles = None

    @property
    def all_paragraphs(self):
        """Return all elements from ODT file defined as either a header or a
        paragraph. Note: Some definied paragraphs have no text, some have no
        defined style, and some are not intended to be user-editable."""

        return [p for p in self._get_elements_by_nstypes(self.odt, ("h", "p"))]

    @property
    def all_spans(self):
        return [s for s in self._get_elements_by_nstypes(self.odt, ("span",))]

    @property
    def name(self):
        return self.file_path.name

    @property
    def number(self):
        num_match = self.RE_2_DIGITS.search(self.file_path.stem)
        if "TOC" in self.file_path.name:
            return 0
        elif num_match:
            return int(num_match[0])

    @property
    def odt(self):
        if self._odt is None:
            self._odt = load(self.file_path)
        return self._odt

    def _get_elements_by_nstypes(self, node, nstypes, accumulator=None):
        """Return valid "paragraph" elements in document order to preserve
        indexing."""
        qnames = [(TEXTNS, t) for t in nstypes]
        if accumulator is None:
            accumulator = list()

        # If "node" is a document, choose its top Node.
        if not hasattr(node, "qname"):
            node = node.topnode

        if node.qname in qnames:
            accumulator.append(node)

        for e in node.childNodes:
            if e.nodeType == Node.ELEMENT_NODE:
                accumulator = self._get_elements_by_nstypes(e, nstypes, accumulator)

        return accumulator

    @property
    def paragraphs(self):
        """Return list of user-editable paragraphs."""
        paragraphs = []
        for p_node in self.all_paragraphs:
            if len(extractText(p_node)) == 0:
                continue
            if p_node.getAttribute("stylename") in self.styles:
                paragraphs.append(OdtParagraph(p_node, chapter=self))
        return paragraphs

    @property
    def styles(self):
        """Return list of valid styles for translatable paragraphs and spans."""

        if self._styles is None:
            styles = dict()
            nodes = [n for n in self.all_paragraphs]
            nodes.extend([n for n in self.all_spans])
            for node in nodes:
                # Ignore spans with no style info.
                if node.getAttribute("stylename") is None:
                    continue
                # Ignore spans with no text.
                if len(extractText(node)) == 0:
                    continue
                style_name = node.getAttribute("stylename")
                if style_name in self.sfm_ref.keys():
                    styles[style_name] = self.sfm_ref.get(style_name)
            self._styles = styles
        return self._styles

    @property
    def sfm(self):
        # Initialize data.
        out_text = list()
        # Add "chapter" info.
        if self.number > 0:
            out_text.append(f"\\c {self.number}")
        # Add lines from ODT document.
        for p in self.paragraphs:
            # Ignore paragraphs with no style info.
            if p.style is None:
                continue
            # Ignore paragraphs with no text.
            if len(p.text) == 0:
                continue

            line = ""
            # See if corresponding SFM exists in reference table.
            sfm = self.sfm_ref.get(p.style)
            if sfm:
                line = f"{sfm} {p.text}"
            if len(p.spans) > 0:
                # If span text is identical to paragraph text, use the span's
                # style instead of paragraph's style (e.g. ODT lists).
                s1 = p.spans[0]
                if p.text == s1.text:
                    sfm = self.sfm_ref.get(s1.style)
                    line = f"{sfm} {s1.text}"
                # If span(s) are a subset of paragraph text, try to apply inline
                # formatting.
                else:
                    for s in p.spans:
                        sfm_inline = self.sfm_ref.get(s.style)
                        if sfm_inline and len(s.text) > 0:
                            s_inline = f"{sfm_inline} {s.text}{sfm_inline}*"
                            line = line.replace(s.text, s_inline)

            # Add SFM line.
            if len(line) > 0:
                out_text.append(line)
        return "\n".join(out_text)

    @property
    def sfm_ref(self):
        if not self._sfm_ref:
            self._sfm_ref = dict()
            ref_file = Path(__file__).parents[2] / "ref.txt"
            for line in ref_file.read_text().splitlines():
                try:
                    k, v = line.split("\\")
                    self._sfm_ref[k.strip()] = f"\\{v.strip()}"
                except ValueError as e:
                    raise ValueError(f"{e}: {line}")
        return self._sfm_ref

    @sfm_ref.setter
    def sfm_ref(self, value):
        if not isinstance(value, dict):
            raise ValueError("Must be instance of `dict`.")
        else:
            self._sfm_ref = value

    @property
    def all_styles(self):
        if self._all_styles is None:
            styles = []
            for p in self.paragraphs:
                if p.style not in styles:
                    styles.append(p.style)
            self._all_styles = styles
        return self._all_styles

    def all_styles_and_paragraphs(self):
        raise NotImplementedError
        data = []
        for p in self.all_paragraphs:
            data.append(f"[{p.style}] {p.text}")
            for s in p.spans:
                data.append(f"> [{s.style}] {s.text}")
        return data

    # def save(self):
    #     path = Path(outfile_path)
    #     if not path.is_file():
    #         raise FileNotFoundError

    # def export_sfm(self):
    #     outfile = Path(self.name).with_suffix(".sfm")
    #     outfile.write_text(self.sfm)

    # def export_styles_and_text(self):
    #     outfile = Path(self.name).with_suffix(".txt")
    #     outfile.write_text("\n".join(self.all_styles_and_paragraphs()))

    def __str__(self):
        return self.name


class OdtToc(OdtChapter):
    RE_LETTER_BEFORE_DIGITS = re.compile(r"(?<=[a-z])[0-9]+")
    INTRO_MARKERS = (
        "\\mt",
        "\\s",
        "\\p",
        "\\pi",
        "\\m",
        "\\mi",
        "\\pq",
        "\\mq",
        "\\q",
        "\\b",
        "\\li",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert "normal" SFMs to Intro-specific SFMs.
        for pstyle, sfm in self.sfm_ref.items():
            sfm_intro = self.to_intro_sfm(sfm)
            self.sfm_ref[pstyle] = sfm_intro

    @classmethod
    def to_intro_sfm(cls, sfm):
        # Strip any #s from SFM tags.
        # sfm_plain = re.sub(cls.RE_LETTER_BEFORE_DIGITS, "", sfm)
        sfm_plain = cls.RE_LETTER_BEFORE_DIGITS.sub("", sfm)
        if sfm_plain in cls.INTRO_MARKERS:
            # Get trailing digits.
            sfm_digits = sfm.split(sfm_plain)[1]
            # Add intro "i" in front of marker.
            return f"\\i{sfm_plain[1:]}{sfm_digits}"
        else:
            return sfm


class OdtBook:
    """The full content of all of "Lessons from Luke" lessons, which is a
    sequence of ODT files in a single parent folder."""

    def __init__(self, dir=None, lang=None):
        self._dir_path = None
        self._language = lang
        if dir is None:
            raise ValueError("No folder was given.")
        else:
            self.dir_path = dir

    def __str__(self):
        return self.name

    @property
    def dir_path(self):
        return self._dir_path

    @dir_path.setter
    def dir_path(self, value):
        dir_path = Path(value)
        if not dir_path.is_dir():
            raise ValueError(f"Not a valid folder: {value}")
        self._dir_path = dir_path

    @property
    def language(self):
        if self._language is None:
            self._language = ""
        return self._language

    @language.setter
    def language(self, value):
        self._language = str(value)

    @property
    def chapters(self):
        chapters = dict()
        chapter_files = sorted(
            [f for f in self.dir_path.iterdir() if f.suffix == ".odt"]
        )
        for lf in chapter_files:
            chapter = OdtChapter(lf)
            if chapter.number == 0:
                chapter = OdtToc(lf)
            chapters[chapter.number] = chapter
        return chapters

    @property
    def name(self):
        return self.dir_path.name

    # @property
    # def sfm(self):
    #     # Initialize data.
    #     out_text = list()
    #     # Add "book" info.
    #     out_text.append(
    #         f'\\id XXA "{self.name}"; generated by "{__file__}" at {self.timestamp()}'
    #     )
    #     out_text.append("\\usfm 3.0")
    #     # Add lines from lessons.
    #     for chapter in self.chapters:
    #         out_text.append(chapter.sfm)
    #     return "\n".join(out_text)


def print_styles(book):
    all_styles = []
    for chapter in book.chapters:
        print(chapter.name)
        for i, style in enumerate(sorted(chapter.styles)):
            if style not in all_styles:
                all_styles.append(style)
            print(f" {i:2d}: {style}")
        print()

    print("All styles:")
    for i, style in enumerate(all_styles):
        print(f" {i:2d}: {style}")
