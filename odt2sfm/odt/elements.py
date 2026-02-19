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

    def to_sfm(self):
        pass

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
        return self._get_children_from_node(self.node)

    @property
    def spans(self):
        spans = []
        for child in self.children:
            if isinstance(child, OdtSpan):
                spans.append(child)
        return spans

    @property
    def style(self):
        return self.node.style

    def _get_children_from_node(self, node, accumulator=None):
        if accumulator is None:
            accumulator = list()

        # We re-interpret text as a "child" for cleaner looping.
        if node.text:
            if node.text.replace(" ", "").replace("\t", "") != "":
                accumulator.append(OdtText(node.text, node, chapter=self.chapter))
            else:
                # logging.debug(f"{node.__dir__()}")
                logging.debug(f"Excluding text w/ only space from: {node.tag}")

        # Evaluate node children.
        for child_node in node.children:
            accumulator = self._get_children_from_node(child_node, accumulator)

        # As with text, we re-interpret any "tail" as a final child node.
        if node.tail:
            if node.tail.replace(" ", "").replace("\t", "") != "":
                accumulator.append(
                    OdtText(node.tail, node, tail=True, chapter=self.chapter)
                )
            else:
                logging.debug(f"Excluding tail w/ only space from: {node.tag}")

        return accumulator

    def update_text(self, sfm_paragraph):
        """Starting with the paragraph node, recursively check for Text nodes
        and update their data if needed."""
        # Only proceed if overall paragraph text is different.
        if self.text == self._normalize(sfm_paragraph.text):
            logging.debug(f"Skipping unchanged paragraph: {sfm_paragraph.intro}")
            return

        odt_ct = len(self.children)
        sfm_ct = len(sfm_paragraph.children)
        if odt_ct != sfm_ct:
            logging.warning(
                f"Warning: Unmatched children for ODT ({odt_ct}) & SFM ({sfm_ct}): {self.intro}|{sfm_paragraph.intro}"
            )
            logging.debug(
                [f'{c.__class__.__name__}:"{c.text}":"{c.tail}"' for c in self.children]
            )
            logging.debug(
                [f'{c.__class__.__name__}:"{c.text}"' for c in sfm_paragraph.children]
            )
            logging.debug(f"{self.all_children=}")
            return

        logging.debug(
            f"P children: {[f'{c.__class__.__name__}:{c.text}' for c in self.children]}"
        )
        logging.debug(
            f"XML children: {[f'{c.text=}; {c.tail=}' for c in self.node.children]}"
        )
        for i, odt_item in enumerate(self.children):
            sfm_item = sfm_paragraph.children[i]
            if isinstance(odt_item, OdtText):
                # Set odt_paragraph.text or odt_text.tail value.
                if not odt_item.is_tail:
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
