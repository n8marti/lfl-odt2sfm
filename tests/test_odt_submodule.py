import unittest
from pathlib import Path

from odt2sfm.odt import OdtChapter
from odt2sfm.odt.elements import OdtParagraph, OdtSpan

# from odt2sfm.odt.elements import OdtElement, OdtParagraph, OdtSpan

BOOK_PATH = Path(__file__).parent / "data" / "book.odt"


class TestOdtElements(unittest.TestCase):
    def setUp(self):
        self.chapter = OdtChapter(BOOK_PATH)
        self.paragraph3 = OdtParagraph(
            self.chapter.all_paragraphs[3], chapter=self.chapter
        )
        self.paragraph4 = OdtParagraph(
            self.chapter.all_paragraphs[4], chapter=self.chapter
        )
        self.span_normal = OdtSpan(self.chapter.all_spans[2])
        self.span_tabs = OdtSpan(self.chapter.all_spans[3])

    def test_paragraph_text(self):
        self.assertEqual("3 3rd verse, but now 2nd paragraph.", self.paragraph4.text)

    def test_path(self):
        self.assertEqual(self.paragraph3.path, "document/body/text/p")

    def test_span_text_simple(self):
        self.assertEqual("bolded", self.span_normal.text)

    def test_span_text_withtabs(self):
        self.assertEqual("boldwithtabs", self.span_tabs.text)
