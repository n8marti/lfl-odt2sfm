import unicodedata

from odf.element import Node
from odf.teletype import extractText


class OdtElement:
    def __init__(self, element, chapter=None):
        self.node = element
        self.chapter = None
        # FIXME: Normalization form should come from ODT file somehow.
        self.normalization_form = "NFC"
        if chapter:
            self.chapter = chapter

    @property
    def all_children(self):
        return self.node.childNodes

    @property
    def parent(self):
        return self.node.parentNode

    @property
    def path(self):
        node = self.node
        path = [node.qname[1] if node.nodeType == Node.ELEMENT_NODE else str(node)]
        while node.parentNode is not None:
            path.insert(0, node.parentNode.qname[1])
            node = node.parentNode
        return "/".join(path)

    @property
    def text(self):
        # Note: Using extractText allows special spacings (e.g. line breaks,
        # tabs, multiple spaces) to be properly converted to unicode, but this
        # misrepresents whether or not the SFM text has been changed from the
        # original ODT text, since those special spacings aren't exported as
        # editable in the SFM output.
        # return extractText(self.node)
        return str(self.node)

    def _normalize(self, text):
        """Normalize foreign text according to current document preferences."""
        return unicodedata.normalize(self.normalization_form, text)

    def __str__(self):
        return self.text


class OdtText(OdtElement):
    @property
    def data(self):
        return self.node.data

    @property
    def text(self):
        return self.data


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self.node.getAttribute("stylename")


class OdtParagraph(OdtElement):
    @property
    def children(self):
        children = []
        for node in self.all_children:
            if node.nodeType == Node.TEXT_NODE:
                if len(node.data) > 0:  # ignore nodes with zero characters
                    # print(f"|{node.data}|")
                    children.append(node)
            elif node.nodeType == Node.ELEMENT_NODE:
                if node.qname[1] == "span":
                    # from sys import stdout

                    # print(node.toXml(0, stdout))
                    if node.getAttribute("stylename") in self.chapter.styles:
                        children.append(node)
        return children

    @property
    def spans(self):
        def descendent_of_node(node, ancestor):
            while node:
                if node is ancestor:
                    return True
                # NOTE: Top node has no parentNode.
                node = node.parentNode

        spans = []
        # FIXME: Loop through self.node.getElementsByType instead.
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

    # @property
    # def texts(self):
    #     texts = []
    #     if self.spans:  # texts are only relevant if there are spans
    #         for c in self.node.childNodes:
    #             if c.nodeType == Node.TEXT_NODE and c.data.replace(" ", "") != "":
    #                 texts.append(c)
    #     else:
    #         # Assume first Text node is paragraph text.
    #         for c in self.node.childNodes:
    #             if c.nodeType == Node.TEXT_NODE:
    #                 # TODO: What if 1st text node is a space/tab/line-break?
    #                 print(f"{c.data=}")
    #                 texts.append(c)
    #                 break
    #     return texts

    def update_text(self, sfm_paragraph):
        """Starting with the paragraph node, recursively check for Text nodes
        and update their data if needed."""
        # Only proceed if overall paragraph text is different.
        if self.text == self._normalize(sfm_paragraph.text):
            print(f"Skipping unchanged paragraph: {sfm_paragraph.text[:20]}...")
            return
        # print(f"\n{self.text}\n{self._normalize(sfm_paragraph.text)}\n")
        odt_ct = len(self.children)
        sfm_ct = len(sfm_paragraph.children)
        if odt_ct != sfm_ct:
            print(f"Warning: Unmatched children for ODT ({odt_ct}) & SFM ({sfm_ct})")
            print([c.__class__.__name__ for c in self.children])
            texts = []
            for c in self.children:
                if c.nodeType == Node.TEXT_NODE:
                    texts.append(c.data)
                else:
                    texts.append(str(c))
            print(texts)
            print([c.__class__.__name__ for c in sfm_paragraph.children])
            print([c.text for c in sfm_paragraph.children])
            print(extractText(self.node))
            print()
            return

        self._update_node_text(self.node, sfm_paragraph)

    def _update_node_text(self, node, sfm_paragraph):
        """Update node text by editing child Text nodes recursively."""

        # def compare_nodes(node, children):
        #     idx = None
        #     for i, n in enumerate(self.children):
        #         if node is n:
        #             idx = i
        #     if idx is not None:
        #         return id
        # if hasattr(node, "qname"):
        #     print(f"{node.qname[1]=}")
        print(
            f"{self.node.qname[1]}:{[c.qname[1] for c in self.children if hasattr(c, 'qname')]}"
        )

        idx = None
        for i, n in enumerate(self.children):
            if node is n:
                idx = i
                break
        if idx is None:
            # Node does not have updatable text.
            print(
                f"Skipping ignored node: {node.parentNode.qname[1]}/{node.qname[1]}: {str(node)}"
            )
            # print(f"{self.node=}; {self.children=}")
            # print(f"{[n.__class__.__name__ for n in node.childNodes]}")
            return

        sfm_text = self._normalize(sfm_paragraph.children[idx])
        if node.nodeType == Node.TEXT_NODE:
            if node.data != sfm_text:
                print(
                    f"Updating text for: {node.parentNode.getAttribute('stylename')}; from '{node.data}' to '{sfm_text}'"
                )
                node.data = sfm_text
        elif node.nodeType == Node.ELEMENT_NODE:
            if extractText(node) != sfm_text:
                for child_node in node.childNodes:
                    self._update_node_text(child_node, sfm_paragraph)
