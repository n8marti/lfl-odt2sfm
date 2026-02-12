from odf.teletype import extractText
from odf.text import P, Span


class OdtElement:
    def __init__(self, element):
        self.node = element

    @property
    def parent(self):
        return self.node.parentNode

    @property
    def text(self):
        # Note: Using extractText allows special spacings (e.g. line breaks,
        # tabs, multiple spaces) to be properly converted to unicode.
        return extractText(self.node)

    def __str__(self):
        return self.text


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self.node.getAttribute("stylename")


class OdtParagraph(OdtElement):
    @property
    def spans(self):
        return [OdtSpan(s) for s in self.node.getElementsByType(Span)]

    @property
    def style(self):
        return self.node.getAttribute("stylename")

    def update_text(self, sfm_paragraph):
        # Update non-Span text.
        if self.text != sfm_paragraph.text:
            new_paragraph = P(
                attributes={"stylename": self.style},
                text=sfm_paragraph.text,
            )
            # Update span texts.
            if len(sfm_paragraph.spans) == len(self.spans):
                print(f"{self.node.childNodes=}")
                for sfm_s, odt_s in zip(sfm_paragraph.spans, self.spans):
                    print(f"{odt_s.node.__dict__=}")
                    new_span = Span(
                        attributes={"stylename": self.style},
                        text=sfm_s.text,
                    )
                    new_paragraph.insertBefore(new_span, odt_s.node)
                    new_paragraph.removeChild(odt_s.node)
            new_paragraph = self.parent.insertBefore(new_paragraph, self.node)
            self.parent.removeChild(self.node)
            self.node = new_paragraph
