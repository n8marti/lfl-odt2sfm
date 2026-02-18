import unicodedata

from odfdo import Element, EText


class OdtElement:
    def __init__(self, node, chapter=None):
        self.node = node
        self.chapter = None
        # FIXME: Normalization form should come from ODT file somehow.
        self.normalization_form = "NFC"
        if chapter:
            self.chapter = chapter

    @property
    def all_children(self):
        return self.node.children

    @property
    def parent(self):
        return self.node.parent

    @property
    def path(self):
        node = self.node
        path = [node.tag if isinstance(node, Element) else str(node)]
        while node.parent is not None:
            path.insert(0, node.parent.tag)
            node = node.parent
        return "/".join(path)

    @property
    def text(self):
        return self.node.text_recursive

    def _normalize(self, text):
        """Normalize foreign text according to current document preferences."""
        return unicodedata.normalize(self.normalization_form, text)

    def __str__(self):
        return self.text


class OdtText(OdtElement):
    @property
    def data(self):
        return self.node

    @property
    def text(self):
        return self.node


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self.node.get_attribute("text:style-name")

    @property
    def text(self):
        return self.node.inner_text


class OdtParagraph(OdtElement):
    @property
    def children(self):
        def _filter_children(node, accumulator=None):
            if accumulator is None:
                accumulator = []
            if node.text:
                accumulator.append(node.text)
            if node.tail:
                accumulator.append(node.tail)
            for child in node.children:
                if child.tag in ("text:paragraph", "text:span"):
                    if child.style in self.chapter.styles:
                        accumulator.append(child)
                else:
                    accumulator = _filter_children(child, accumulator)
            return accumulator

        print(f"children: checking: {self.node.tag}/{self.all_children=}")
        children = _filter_children(self.node)

        return children

    @property
    def spans(self):
        def descendent_of_node(node, ancestor):
            while node:
                if node is ancestor:
                    return True
                # NOTE: Top node has no parent.
                node = node.parent

        spans = []
        for c_node in self.children:
            print(f"Checking: {c_node.tag}")
            # Ignore non-span nodes..
            if c_node.tag != "text:span":
                print(f"Skipping: {c_node.tag}")
                continue
            print(f"Keeping: {c_node.tag}")
            # Ignore spans that contain the full paragraph's text.
            if c_node.text == self.text:
                continue
            # Ignore spans whose style is not in the useful styles list.
            if c_node.get_attribute("text:style-name") not in self.chapter.styles:
                continue
            spans.append(OdtSpan(c_node))
        return spans

    @property
    def style(self):
        return self.node.get_attribute("text:style-name")

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
            # for c in self.children:
            #     if c.nodeType == Node.TEXT_NODE:
            #         texts.append(c.data)
            #     else:
            #         texts.append(str(c))
            print(texts)
            print([c.__class__.__name__ for c in sfm_paragraph.children])
            print([c.text for c in sfm_paragraph.children])
            # print(extractText(self.node))
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
        # print(
        #     f"{self.node.qname[1]}:{[c.qname[1] for c in self.children if hasattr(c, 'qname')]}"
        # )

        idx = None
        for i, n in enumerate(self.children):
            if node is n:
                idx = i
                break
        if idx is None:
            # Node does not have updatable text.
            # print(
            #     f"Skipping ignored node: {node.parentNode.qname[1]}/{node.qname[1]}: {str(node)}"
            # )
            # print(f"{self.node=}; {self.children=}")
            # print(f"{[n.__class__.__name__ for n in node.childNodes]}")
            return

        sfm_text = self._normalize(sfm_paragraph.children[idx])
        if isinstance(node, EText):
            if node != sfm_text:
                print(
                    f"Updating text for: {node.parent.get_attribute('text:style-name')}; from '{node}' to '{sfm_text}'"
                )
                node = EText(sfm_text)
        elif isinstance(node, Element):
            if node.text_recursive != sfm_text:
                for child_node in node.children:
                    self._update_node_text(child_node, sfm_paragraph)
