from odf.text import Span


class OdtElement:
    def __init__(self, element):
        self._element = element

    def __str__(self):
        return str(self._element)

    @property
    def text(self):
        return str(self)


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self._element.getAttribute("stylename")


class OdtParagraph(OdtElement):
    @property
    def spans(self):
        return [OdtSpan(s) for s in self._element.getElementsByType(Span)]

    @property
    def style(self):
        return self._element.getAttribute("stylename")
