import re
from pathlib import Path


class SfmChapter:
    """A complete SFM Chapter, with one or more paragraphs and zero or more verses."""

    def __init__(self, raw_sfm=None):
        self._number = None
        self._odt_styles = None
        self._sfm_raw = None
        self._verses = None
        if raw_sfm is not None:
            self.sfm_raw = raw_sfm

    @property
    def number(self):
        if self._number is None:
            m = re.match(r"^\\c ([0-9]+)", self.sfm_raw)
            if m:
                self._number = int(m[1])
            else:
                raise ValueError(
                    f"No chapter number found: {self.sfm_raw.splitlines()[0]}..."
                )
        return self._number

    @property
    def odt_styles(self):
        if self._odt_styles is None:
            styles = dict()
            ref_file = Path(__file__).parents[2] / "ref.txt"
            for line in ref_file.read_text().splitlines():
                try:
                    k, v = line.split("\\")
                    k = k.strip()
                    v = f"\\{v.strip()}"
                    if not styles.get(v):
                        styles[v] = []
                    styles[v].append(k)
                except ValueError as e:
                    raise ValueError(f"{e}: {line}")
            self._odt_styles = styles.copy()
        return self._odt_styles

    @property
    def sfm_raw(self):
        return self._sfm_raw

    @sfm_raw.setter
    def sfm_raw(self, value):
        self._sfm_raw = value

    @property
    def verses(self):
        if self._verses is None:
            verses = []
            init = True
            for v in re.split(r"\\v ", self.sfm_raw):
                if init:  # skip first "split", which is not a verse
                    init = False
                    continue
                sfm_raw = f"\\v {v.rstrip()}"
                # TODO: Do we need to preserve chapter numbers for some reason?
                verses.append(sfm_raw)
            self._verses = verses.copy()
        return self._verses

    def __str__(self):
        return self.sfm_raw


class SfmBook:
    """A complete SFM file with one or more Chapters."""

    def __init__(self, file_path=None):
        self._chapters = None
        self._file_path = None
        self._id_text = None
        self._name = None
        self._sfm_raw = None
        if file_path is not None:
            self.file_path = file_path

    def __str__(self):
        return self.name

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, value):
        self._file_path = Path(value)

    @property
    def id_text(self):
        if self._id_text is None:
            m = re.search(r"\\id (.*)\n", self.sfm_raw)
            if m:
                self._id_text = m[1]
        return self._id_text

    @property
    def name(self):
        if self._name is None:
            if self.file_path is not None:
                self._name = self.file_path.name
            else:
                self._name = ""
        return self._name

    @property
    def sfm_raw(self):
        if self._sfm_raw is None:
            self._sfm_raw = self.file_path.read_text()
        return self._sfm_raw

    @property
    def chapters(self):
        if self._chapters is None:
            chapters = []
            init = True
            for c in re.split(r"\\c ", self.sfm_raw):
                if init:
                    sfm_raw = c.rstrip()
                    init = False
                else:
                    sfm_raw = f"\\c {c.rstrip()}"
                # TODO: Do we need to preserve chapter numbers for some reason?
                chapters.append(SfmChapter(sfm_raw))
            self._chapters = chapters.copy()
        return self._chapters
