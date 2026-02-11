import re
import sys
from datetime import datetime
from pathlib import Path

from odf.opendocument import load
from odf.text import P

from odt.elements import OdtParagraph


class Lesson:
    REGEX_2DIGITS = re.compile(r"[0-9]{2}")

    def __init__(self, file_path=None):
        if file_path is None:
            raise ValueError("No file path was given for this lesson.")
        else:
            self.file_path = Path(file_path)
        if not self.file_path.is_file():
            raise ValueError(f"File does not exist: {self.file_path}")

        self._sfm_ref = None
        self._styles = None

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.file_path.name

    @property
    def number(self):
        num_match = re.search(self.REGEX_2DIGITS, self.file_path.stem)
        if "TOC" in self.file_path.name:
            return 0
        elif num_match:
            return int(num_match[0])

    @property
    def odt(self):
        return load(self.file_path)

    @property
    def paragraphs(self):
        return [OdtParagraph(p) for p in self.odt.getElementsByType(P)]

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
            ref_file = Path("ref.txt")
            for line in ref_file.read_text().splitlines():
                try:
                    k, v = line.split("\\")
                    self._sfm_ref[k.strip()] = f"\\{v.strip()}"
                except ValueError as e:
                    raise ValueError(f"{e}: {line}")
        return self._sfm_ref

    @property
    def styles(self):
        if self._styles is None:
            styles = []
            for p in self.paragraphs:
                if p.style not in styles:
                    styles.append(p.style)
            self._styles = styles
        return self._styles

    @sfm_ref.setter
    def sfm_ref(self, value):
        if not isinstance(value, dict):
            raise ValueError("Must be instance of `dict`.")
        else:
            self._sfm_ref = value

    def all_styles_and_paragraphs(self):
        data = []
        for p in self.paragraphs:
            data.append(f"[{p.style}] {p.text}")
            for s in p.spans:
                data.append(f"> [{s.style}] {s.text}")
        return data

    def export_sfm(self):
        outfile = Path(self.name).with_suffix(".sfm")
        outfile.write_text(self.sfm)

    def export_styles_and_text(self):
        outfile = Path(self.name).with_suffix(".txt")
        outfile.write_text("\n".join(self.all_styles_and_paragraphs()))


class Toc(Lesson):
    REGEX_LETTERBEFOREDIGITS = re.compile(r"(?<=[a-z])[0-9]+")
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
        sfm_plain = re.sub(cls.REGEX_LETTERBEFOREDIGITS, "", sfm)
        if sfm_plain in cls.INTRO_MARKERS:
            # Get trailing digits.
            sfm_digits = sfm.split(sfm_plain)[1]
            # Add intro "i" in front of marker.
            return f"\\i{sfm_plain[1:]}{sfm_digits}"
        else:
            return sfm


class Book:
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
    def lessons(self):
        lessons = list()
        lesson_files = sorted(
            [f for f in self.dir_path.iterdir() if f.suffix == ".odt"]
        )
        last_file = lesson_files.pop()
        toc_lesson = None
        if "TOC" in last_file.name:
            # File is Table of Contents.
            toc_lesson = Toc(last_file)
            # Put lesson at the beginning.
            lessons.append(toc_lesson)
        for lf in lesson_files:
            lessons.append(Lesson(lf))
        if toc_lesson is None:
            # Re-add last lesson file.
            lessons.append(Lesson(last_file))
        return lessons

    @property
    def name(self):
        return self.dir_path.name

    @property
    def sfm(self):
        # Initialize data.
        out_text = list()
        # Add "book" info.
        out_text.append(
            f'\\id XXA "{self.name}"; generated by "{__file__}" at {self.timestamp}'
        )
        out_text.append("\\usfm 3.0")
        # Add lines from lessons.
        for lesson in self.lessons:
            out_text.append(lesson.sfm)
        return "\n".join(out_text)

    @property
    def timestamp(self):
        return datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    def export_sfm(self):
        raise NotImplementedError
        # outfile = Path(self.name).with_suffix(".sfm")
        # outfile.write_text(self.sfm)


def print_sfm(item):
    """Print full book's or single lesson's SFM-encoded text."""
    print(item.sfm)


def print_styles(book):
    all_styles = []
    for lesson in book.lessons:
        print(lesson.name)
        for i, style in enumerate(sorted(lesson.styles)):
            if style not in all_styles:
                all_styles.append(style)
            print(f" {i:2d}: {style}")
        print()

    print("All styles:")
    for i, style in enumerate(all_styles):
        print(f" {i:2d}: {style}")


def main():
    book = Book(sys.argv[1])
    # print_styles(book)
    # print_sfm(book)
    lesson = book.lessons[1]
    lesson.export_sfm()
    lesson.export_styles_and_text()


if __name__ == "__main__":
    main()
