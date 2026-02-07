from odf.text import Span as ODTSpan


class Element:
    def __init__(self, element):
        self._element = element

    def __str__(self):
        return str(self._element)

    @property
    def text(self):
        return str(self)


class Span(Element):
    @property
    def style(self):
        return self._element.getAttribute("stylename")


class Paragraph(Element):
    @property
    def spans(self):
        return [Span(s) for s in self._element.getElementsByType(ODTSpan)]

    @property
    def style(self):
        return self._element.getAttribute("stylename")
