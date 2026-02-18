import unittest
from pathlib import Path

from odt2sfm.odt import OdtChapter
from odt2sfm.odt.elements import OdtParagraph, OdtSpan

CHAPTER_PATH = Path(__file__).parent / "data" / "chapter.odt"


class TestOdtChapter(unittest.TestCase):
    def setUp(self):
        self.chapter = OdtChapter(CHAPTER_PATH)

    def test_chapter_paragraphs(self):
        self.assertEqual(len(self.chapter.all_paragraphs), 8)
        self.assertEqual(
            len(self.chapter.odt.body.paragraphs) + len(self.chapter.odt.body.headers),
            8,
        )


class TestOdtElements(unittest.TestCase):
    def setUp(self):
        self.chapter = OdtChapter(CHAPTER_PATH)
        self.paragraph3 = OdtParagraph(
            self.chapter.all_paragraphs[2], chapter=self.chapter
        )
        self.paragraph4 = OdtParagraph(
            self.chapter.all_paragraphs[3], chapter=self.chapter
        )
        self.span_bold = OdtSpan(self.chapter.all_spans[2])
        self.span_tabs = OdtSpan(self.chapter.all_spans[3])

    def test_paragraph_spans(self):
        self.assertEqual(len(self.chapter.all_spans), 7)

    def test_paragraph_text(self):
        self.assertEqual("3 3rd verse, but now 2nd paragraph.", self.paragraph4.text)

    def test_path(self):
        self.assertEqual(
            self.paragraph3.path,
            "office:document-content/office:body/office:text/text:p",
        )

    def test_span_text_simple(self):
        self.assertEqual("bolded", self.span_bold.text)

    def test_span_text_withtabs(self):
        self.assertEqual("bold\twith\ttabs.", self.span_tabs.text)
