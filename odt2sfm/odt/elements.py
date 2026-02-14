from odf.element import Node
from odf.namespaces import TEXTNS
from odf.teletype import extractText


class OdtElement:
    def __init__(self, element, chapter=None):
        self.node = element
        self.chapter = None
        if chapter:
            self.chapter = chapter

    @property
    def parent(self):
        return self.node.parentNode

    @property
    def text(self):
        # Note: Using extractText allows special spacings (e.g. line breaks,
        # tabs, multiple spaces) to be properly converted to unicode.
        return self._extract_text()

    def _extract_text(self, before_span=False):
        """Extract text content from an Element, with whitespace represented
        properly. Returns the text, with tabs, spaces, and newlines
        correctly evaluated. This method recursively descends through the
        children of the given element, accumulating text and "unwrapping"
        <text:s>, <text:tab>, and <text:line-break> elements along the way.
        """
        result = []

        if len(self.node.childNodes) != 0:
            for child in self.node.childNodes:
                if child.nodeType == Node.TEXT_NODE:
                    result.append(child.data)
                elif child.nodeType == Node.ELEMENT_NODE:
                    sub_element = child
                    tag_name = sub_element.qname
                    if before_span is True and tag_name == (TEXTNS, "span"):
                        # Don't "gather" text from span elements.
                        break
                    if tag_name == (TEXTNS, "line-break"):
                        result.append("\n")
                    elif tag_name == (TEXTNS, "tab"):
                        result.append("\t")
                    elif tag_name == (TEXTNS, "s"):
                        c = sub_element.getAttribute("c")
                        if c:
                            spaceCount = int(c)
                        else:
                            spaceCount = 1

                        result.append(" " * spaceCount)
                    else:
                        result.append(extractText(sub_element))

        return "".join(result)

    def __str__(self):
        return self.text


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self.node.getAttribute("stylename")


class OdtParagraph(OdtElement):
    @property
    def spans(self):
        def descendent_of_node(node, ancestor):
            while node:
                if node is ancestor:
                    return True
                # NOTE: Top node has no parentNode.
                node = node.parentNode

        spans = []
        for s_node in self.chapter.all_spans:
            # Ignore spans that are contained within other paragraphs.
            if not descendent_of_node(s_node, self.node):
                continue
            # Ignore spans that contain the full paragraph's text.
            if extractText(s_node) == self.text:
                continue
            # Ignore spans whose style is not in the useful styles list.
            if s_node.getAttribute("stylename") not in self.chapter.styles:
                continue
            spans.append(OdtSpan(s_node))
        return spans

    @property
    def style(self):
        return self.node.getAttribute("stylename")

    @property
    def texts(self):
        texts = []
        if self.spans:  # texts are only relevant if there are spans
            for c in self.node.childNodes:
                if c.nodeType == Node.TEXT_NODE and c.data.replace(" ", "") != "":
                    texts.append(c)
        return texts

    def update_text(self, sfm_paragraph):
        # Only proceed if overall paragraph text is different.
        if self.text == sfm_paragraph.text:
            return

        if len(self.spans) != len(sfm_paragraph.spans):
            print(
                f"Warning: different span count than SFM paragraph: {len(self.spans)} vs {len(sfm_paragraph.spans)}"
            )
            return
        if len(self.texts) != len(sfm_paragraph.texts):
            print(
                f"Warning: different text element count than SFM paragraph: {len(self.texts)} vs {len(sfm_paragraph.texts)}"
            )
            return
        self._update_node_text(self.node, sfm_paragraph)

    def _update_node_text(self, node, sfm_paragraph):
        """Update node text by editing Text child nodes recursively."""
        if node.nodeType == Node.TEXT_NODE:
            idx = None
            for i, t in enumerate(self.texts):
                if node is t:
                    idx = i
                    break
            if idx is None:
                return
            sfm_text = sfm_paragraph.texts[idx]
            if sfm_text != node.data:
                node.data = sfm_text
        elif node.nodeType == Node.ELEMENT_NODE:
            if node.qname[1] == "p":
                if node is self.node:
                    for child_node in node.childNodes:
                        self._update_node_text(child_node, sfm_paragraph)
                else:
                    raise ValueError(
                        f"Unexpected paragraph node in paragraph {self.style}"
                    )
            elif node.qname[1] == "span":
                idx = None
                for i, s in enumerate(self.spans):
                    if node == s.node:
                        idx = i
                        break
                # Check if Span's text needs updating.
                if idx is None:
                    return
                if sfm_paragraph.spans[idx].text != extractText(node):
                    for child_node in node.childNodes:
                        self._update_node_text(child_node, sfm_paragraph)
