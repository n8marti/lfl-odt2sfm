import unittest
from pathlib import Path

from odt2sfm.sfm import SfmBook, SfmChapter
from odt2sfm.sfm.elements import SfmElement, SfmParagraph, SfmSpan

BOOK_PATH = Path(__file__).parent / "data" / "book.sfm"


class TestSfmElements(unittest.TestCase):
    def setUp(self):
        self.element_input = "\\p \\v 19 Sample \\b text\\b*"
        self.span_input = "\\b bolded text\\b*"
        self.element = SfmElement(self.element_input)
        self.span = SfmSpan(self.span_input)

    def test_end_marker(self):
        self.assertEqual(self.span.end_marker, "\\b*")

    def test_marker(self):
        self.assertEqual(self.span.marker, "\\b")

    def test_paragraph_spans(self):
        markers = ["\\v", "\\b", "\\it"]
        end_markers = [None, "\\b*", "\\it*"]
        stexts = ["23", "bolded ", "italicized"]
        texts = [" This is a line of ", "and ", " text."]
        sfm_raws = [
            f"{markers[0]} {stexts[0]}",
            f"{markers[1]} {stexts[1]}{end_markers[1]}",
            f"{markers[2]} {stexts[2]}{end_markers[2]}",
        ]
        p_sfm = f"{sfm_raws[0]}{texts[0]}{sfm_raws[1]}{texts[1]}{sfm_raws[2]}{texts[2]}"
        p = SfmParagraph(p_sfm)
        self.assertEqual(sfm_raws, [s.sfm_raw for s in p.spans])
        self.assertEqual(stexts, [s.text for s in p.spans])
        self.assertEqual(markers, [s.marker for s in p.spans])
        self.assertEqual(end_markers, [s.end_marker for s in p.spans])
        self.assertEqual(texts, p.texts)

    def test_sfm_raw(self):
        self.assertEqual(self.element_input, self.element.sfm_raw)

    def test_text(self):
        self.assertEqual("\\v 19 Sample \\b text\\b*", self.element.text)


class TestSfmBook(unittest.TestCase):
    def test_chapters(self):
        self.book = SfmBook(BOOK_PATH)
        self.assertEqual(len(self.book.chapters), 3)

    def test_id_text(self):
        self.book = SfmBook(BOOK_PATH)
        self.assertEqual("XXA Book title information, etc.", self.book.id_text)


class TestSfmChapter(unittest.TestCase):
    def setUp(self):
        self.book = SfmBook(BOOK_PATH)
        self.c1_raw = (
            "\\c 1\n"
            "\\s Section Header\n"
            "\\p\n"
            "\\v 1 1st verse--nothing fancy.\n"
            "\\v 2 2nd verse with some \\b bolded\\b* text.\n"
            "\\p\n"
            "\\v 3 3rd verse, but now 2nd paragraph.\n"
            "\\s A 2nd Section Header\n"
            "\\q\n"
            '\\v 4 Whatever a verse as "q" is (poetry?)\n'
        )

    def test_chapter_number(self):
        self.assertEqual(self.book.chapters[1].number, 1)

    def test_chapter_number_bad(self):
        c = SfmChapter("\\c  \n\\v 1 Some text.\n")
        with self.assertRaises(ValueError):
            _ = c.number

    # def test_chapter_odt_styles(self):
    #     print(self.book.chapters[1].odt_styles)

    def test_chapter_sfm_raw(self):
        self.assertEqual(self.book.chapters[1].sfm_raw, self.c1_raw)

    def test_chapter_verses(self):
        self.assertEqual(len(self.book.chapters[1].verses), 4)
