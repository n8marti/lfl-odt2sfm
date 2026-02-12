import unittest
from pathlib import Path

from odt2sfm.odt import OdtChapter

# from odt2sfm.odt.elements import OdtElement, OdtParagraph, OdtSpan

BOOK_PATH = Path(__file__).parent / "data" / "book.odt"


class TestOdtElements(unittest.TestCase):
    def setUp(self):
        self.chapter = OdtChapter(BOOK_PATH)
        self.paragraph3 = self.chapter.all_paragraphs[3]
        self.paragraph4 = self.chapter.all_paragraphs[4]
        self.span_normal = self.paragraph3.spans[2]
        self.span_tabs = self.paragraph3.spans[3]

    def test_paragraph_text(self):
        self.assertEqual("3 3rd verse, but now 2nd paragraph.", self.paragraph4.text)

    def test_span_text_simple(self):
        self.assertEqual("bolded", self.span_normal.text)

    def test_span_text_withtabs(self):
        self.assertEqual("bold\twith\ttabs", self.span_tabs.text)


# class TestSfmBook(unittest.TestCase):
#     def test_chapters(self):
#         # self.book = SfmBook(BOOK_PATH)
#         self.assertEqual(len(self.book.chapters), 3)

#     def test_id_text(self):
#         # self.book = SfmBook(BOOK_PATH)
#         self.assertEqual("XXA Book title information, etc.", self.book.id_text)


# class TestSfmChapter(unittest.TestCase):
#     def setUp(self):
#         # self.book = SfmBook(BOOK_PATH)
#         self.c1_raw = (
#             "\\c 1\n"
#             "\\s Section Header\n"
#             "\\p\n"
#             "\\v 1 1st verse--nothing fancy.\n"
#             "\\v 2 2nd verse with some \\b bolded\\b* text.\n"
#             "\\p\n"
#             "\\v 3 3rd verse, but now 2nd paragraph.\n"
#             "\\s A 2nd Section Header\n"
#             "\\q\n"
#             '\\v 4 Whatever a verse as "q" is (poetry?)\n'
#         )

#     def test_chapter_number(self):
#         self.assertEqual(self.book.chapters[1].number, 1)

#     def test_chapter_number_bad(self):
#         c = SfmChapter("\\c  \n\\v 1 Some text.\n")
#         with self.assertRaises(ValueError):
#             _ = c.number

#     def test_chapter_odt_styles(self):
#         print(self.book.chapters[1].odt_styles)

#     def test_chapter_sfm_raw(self):
#         self.assertEqual(self.book.chapters[1].sfm_raw, self.c1_raw)

#     def test_chapter_verses(self):
#         self.assertEqual(len(self.book.chapters[1].verses), 4)
