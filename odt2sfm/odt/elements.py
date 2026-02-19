import logging
import unicodedata

from odfdo import Element


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
    def intro(self):
        """Returns initial characters of text element. Mostly used for logging."""
        if len(self.text_recursive) > 23:
            s = f"{self.text_recursive[:20]}..."
        else:
            s = self.text_recursive
        return s

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
    def tail(self):
        return self.node.tail

    @tail.setter
    def tail(self, value):
        self.node.tail = value

    @property
    def text(self):
        return self.node.text

    @text.setter
    def text(self, value):
        self.node.text = value

    @property
    def text_recursive(self):
        return self.node.text_recursive

    def _normalize(self, text):
        """Normalize foreign text according to current document preferences."""
        return unicodedata.normalize(self.normalization_form, text)

    def __str__(self):
        return self.text_recursive


class OdtText(OdtElement):
    """A text-carrying object. Can be node's `text` or `tail` attribute."""

    def __init__(self, text, parent, tail=False, **kwargs):
        # Pass parent as node to OdtElement.
        super().__init__(parent, **kwargs)
        self.is_tail = tail

    @property
    def tail(self):
        if self.is_tail:
            return self.text

    @property
    def text(self):
        if self.is_tail:
            return self.node.tail
        else:
            return self.node.text

    @text.setter
    def text(self, value):
        if self.is_tail:
            self.node.tail = value
        else:
            self.node.text = value


class OdtSpan(OdtElement):
    @property
    def style(self):
        return self.node.style

    @property
    def text(self):
        # .inner_text includes child nodes, such as tabs and spacers.
        return self.node.inner_text

    @text.setter
    def text(self, value):
        self.node.text = value


class OdtParagraph(OdtElement):
    @property
    def children(self):
        children = []
        # We re-interpret text as a "child" for cleaner looping.
        if self.text and self.text.replace(" ", "") != "":
            children.append(OdtText(self.text, self.node, chapter=self.chapter))
        for child_node in self.node.children:
            # Check for Span type first, which has .style, then check for style attrib.
            if child_node.tag == "text:span":
                if child_node.style in self.chapter.styles:
                    children.append(OdtSpan(child_node, chapter=self.chapter))
                else:
                    logging.info(
                        f"Skipping child w/ excluded style: {child_node.tag}:[{child_node.style}]{child_node.text}"
                    )
            else:
                if child_node.text and child_node.text.replace(" ", "") != "":
                    # logging.debug(f'Adding text: "{child.text}"')
                    children.append(
                        OdtText(child_node.text, child_node, chapter=self.chapter)
                    )
                logging.info(f"Skipping child w/ invalid tag: {child_node.tag}")
            if child_node.tail and child_node.tail.replace(" ", "") != "":
                # logging.debug(f'Adding tail: "{child_node.tail}"')
                children.append(
                    OdtText(
                        child_node.tail, child_node, tail=True, chapter=self.chapter
                    )
                )
        # As with text, we re-interpret any "tail" as a final child node.
        if self.tail and self.tail.replace(" ", "") != "":
            children.append(OdtText(self.tail, tail=True, chapter=self.chapter))

        # logging.debug(f"{self.text_recursive=}; {[c.text for c in children]}")
        return children

    @property
    def spans(self):
        # def descendent_of_node(node, ancestor):
        #     while node:
        #         if node is ancestor:
        #             return True
        #         # NOTE: Top node has no parent.
        #         node = node.parent

        spans = []
        for child in self.children:
            if isinstance(child, OdtSpan):
                spans.append(child)
            # logging.debug(f"Checking: {child.node.tag}")
            # # Ignore non-span nodes..
            # if child.node.tag != "text:span":
            #     logging.debug(f"Skipping: {child.node.tag}")
            #     continue
            # logging.debug(f"Keeping: {child.node.tag}")
            # # Ignore spans that contain the full paragraph's text.
            # if child.text_recursive == self.text_recursive:
            #     continue
            # # Ignore spans whose style is not in the useful styles list.
            # if child.style not in self.chapter.styles:
            #     continue
            # spans.append(child)
        return spans

    @property
    def style(self):
        return self.node.style

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
            logging.debug(f"Skipping unchanged paragraph: {sfm_paragraph.intro}")
            return
        # print(f"\n{self.text}\n{self._normalize(sfm_paragraph.text)}\n")
        odt_ct = len(self.children)
        sfm_ct = len(sfm_paragraph.children)
        if odt_ct != sfm_ct:
            logging.warning(
                f"Warning: Unmatched children for ODT ({odt_ct}) & SFM ({sfm_ct}): {sfm_paragraph.intro}"
            )
            logging.debug([f'{c.__class__.__name__}:"{c.text}"' for c in self.children])
            logging.debug(
                [f'{c.__class__.__name__}:"{c.text}"' for c in sfm_paragraph.children]
            )
            logging.debug("\n")
            return

        prev_odt_item = None
        for i, odt_item in enumerate(self.children):
            sfm_item = sfm_paragraph.children[i]
            if isinstance(odt_item, OdtText):
                # Set odt_paragraph.text or odt_text.tail value.
                if i == 0:
                    logging.info(
                        f'Updating OdtText "{odt_item.intro}" to "{sfm_item.intro}"'
                    )
                else:
                    logging.info(
                        f'Updating OdtText tail "{odt_item.tail}" to "{sfm_item.intro}"'
                    )
                odt_item.text = sfm_item.text
            elif isinstance(odt_item, OdtSpan):
                logging.info(
                    f'Updating OdtSpan "{odt_item.intro}" to "{sfm_item.intro}"'
                )
                odt_item.text = sfm_item.text
            prev_odt_item = odt_item

        # self._update_item_text(self, sfm_paragraph)

    def _update_item_text(self, item, sfm_paragraph):
        """Update [OdtParagraph/OdtSpan/OdtText] item text by editing child Text nodes recursively."""

        for i, child in enumerate(self.children):
            pass
        # Find corresponding item's index in own paragraph's children.
        # idx = self.children.index(item)
        # print(idx)
        return

        if isinstance(item, OdtText):
            # Update text directly.
            pass
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

        # idx = None
        # for i, n in enumerate(self.node.children):
        #     if node is n:
        #         idx = i
        #         break
        # if idx is None:
        #     # Node does not have updatable text.
        #     # print(
        #     #     f"Skipping ignored node: {node.parentNode.qname[1]}/{node.qname[1]}: {str(node)}"
        #     # )
        #     # print(f"{self.node=}; {self.children=}")
        #     # print(f"{[n.__class__.__name__ for n in node.childNodes]}")
        #     return

        # sfm_text = self._normalize(sfm_paragraph.children[idx])
        # if isinstance(node, EText):
        #     if node != sfm_text:
        #         logging.info(
        #             f"Updating text for: {node.parent.get_attribute('text:style-name')}; from '{node}' to '{sfm_text}'"
        #         )
        #         node = EText(sfm_text)
        # elif isinstance(node, Element):
        #     if node.text_recursive != sfm_text:
        #         for child_node in node.children:
        #             self._update_node_text(child_node, sfm_paragraph)
