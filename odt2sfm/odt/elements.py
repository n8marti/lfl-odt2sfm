import logging
import unicodedata

from odfdo import Element, Span

from ..base import do_paratext_replacements, normalize_text
from ..sfm.base import SFM_SPAN_TYPES_NO_END_MARKER, get_sfm_type
from .base import get_node_doc_style


class OdtElement:
    def __init__(self, node, chapter=None):
        self.node = node
        self.chapter = None
        # FIXME: Normalization form should come from ODT file somehow.
        self.normalization_form = "NFC"
        if chapter:
            self.chapter = chapter
        self._path = None
        self._sfm_marker = None

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
        if self._path is None:
            node = self.node
            path = [node.tag if isinstance(node, Element) else str(node)]
            while node.parent is not None:
                path.insert(0, node.parent.tag)
                node = node.parent
            self._path = "/".join(path)
        return self._path

    @property
    def sfm_marker(self):
        if self._sfm_marker is None and hasattr(self, "style"):
            self._sfm_marker = self.chapter.sfm_ref.get(self.style)
        return self._sfm_marker

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
        raise NotImplementedError

    def __str__(self):
        return self.intro


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

    def to_sfm(self):
        return self.text


class OdtSpan(OdtElement):
    """A "span" corresponds to the SFM designation of character-level markers;
    e.g. verses, bold, table columns, etc."""

    @property
    def sfm_marker(self):
        return super().sfm_marker

    @sfm_marker.setter
    def sfm_marker(self, value):
        if not value.startswith("\\"):
            raise ValueError(f"Invalid SFM marker: {value}")
        self._sfm_marker = value

    @property
    def style(self):
        return self.node.style

    @property
    def text(self):
        # .inner_text includes child nodes, such as tabs and spacers.
        # FIXME: This seems a bit hacky, but it works well enough for now.
        if "text:s" or "text:tab" in [c.tag for c in self.node.children]:
            return self.node.inner_text
        else:
            return self.node.text

    @text.setter
    def text(self, value):
        self.node.text = value

    def to_sfm(self):
        # Use span style to get SFM marker.
        sfm_data = ""
        sfm = self.sfm_marker
        if sfm is None:
            raise ValueError(
                f'No SFM span style defined for "{self.style}" in {self.chapter.file_path}'
            )
        if sfm.endswith("v"):
            # Add newline before verse marker.
            sfm_data += "\n"
        sfm_data += f"{sfm} {self.text}"
        sfm_type = get_sfm_type(sfm)
        if sfm_type not in SFM_SPAN_TYPES_NO_END_MARKER:
            # Add ending marker.
            sfm_data += f"{sfm}*"
        return sfm_data


class OdtParagraph(OdtElement):
    """A "paragraph" according to the SFM designation, where all markers are
    either paragraph markers or character markers. This can be a paragraph, a
    heading, a table row, etc."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._children = None
        self._style = None

    @property
    def children(self):
        if self._children is None:
            logging.info(f'Getting children for paragraph "{self}"')
            return self._get_children_from_node(self.node)
        return self._children

    @property
    def spans(self):
        spans = []
        for child in self.children:
            if isinstance(child, OdtSpan):
                spans.append(child)
        return spans

    @property
    def style(self):
        if self._style is None:
            self._style = get_node_doc_style(self.node, self.chapter.odt)
        return self._style

    def _get_children_from_node(self, node, accumulator=None, depth=0):
        """Recurively check the node and its child nodes for those that have
        updatable content."""

        # Only allow recursing one level deeper than original paragraph. This
        # avoids "collecting" text from nested paragraphs.
        if depth > 1:
            return accumulator
        depth += 1

        if accumulator is None:
            accumulator = list()

        # We re-interpret text as a "child" for easier looping.
        if node.text:
            # Skip space-only nodes.
            if node.text.replace(" ", "").replace("\t", "") != "":
                if isinstance(node, Span):
                    child = OdtSpan(node, chapter=self.chapter)
                else:
                    child = OdtText(node.text, node, chapter=self.chapter)
                accumulator.append(child)
            else:
                logging.info(f"Excluding node w/ only space from: {node.tag}")

        # Evaluate node children if not a Span node, b/c "inner_text" is taken
        # from Span node, so child nodes texts' are already incorporated.
        if node.tag != "text:span":
            for child_node in node.children:
                accumulator = self._get_children_from_node(
                    child_node, accumulator, depth=depth
                )

        # As with text, we re-interpret any "tail" as a final child node.
        if node.tail:
            if node.tail.replace(" ", "").replace("\t", "") != "":
                accumulator.append(
                    OdtText(node.tail, node, tail=True, chapter=self.chapter)
                )
            else:
                logging.info(f"Excluding tail w/ only space from: {node.tag}")

        return accumulator

    def to_sfm(self):
        logging.debug(f'Generating SFM output for "{self}"')
        out_text = list()
        sfm = self.sfm_marker
        line = f"{sfm} "
        prev_child = None
        for child in self.children:
            # logging.debug(f"{line=}")
            if isinstance(child, OdtText):
                # Add double-space when following another Text.
                if isinstance(prev_child, OdtText):
                    line += "  "
            line += child.to_sfm()
            prev_child = child

        # Add SFM line.
        if len(line) > 0:
            # Do Paratext replacements.
            line = do_paratext_replacements(line)
            # Normalize characters.
            # FIXME: This should correspond to the Paratext project settings.
            line = normalize_text("NFD", line)
            lines = line.split("\n")
            # logging.debug(f"{lines=}")
            out_text.extend(lines)

        return "\n".join(out_text)

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


class OdtTableRow(OdtParagraph):
    """A TableRow is special paragraph whose children are set manually rather
    than deduced from the node data. All text and styles are found within the
    children elements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._children = list()
        self._parent_table = None

    # TODO: Set correct SFM marker for paragraph.
    @property
    def children(self):
        return self._children

    @property
    def parent_table(self):
        if self._parent_table is None:
            # Parent of table-row node is table node.
            self._parent_table = self.node.parent._xml_element
        return self._parent_table

    @property
    def sfm_marker(self):
        return "\\tr"

    def add_cell(self, node, column_idx):
        """Add the "paragraph" node's data to the table row. This can include
        plain text and span data."""
        # Hijack OdtParagraph to generate child elements.
        p = OdtParagraph(node, chapter=self.chapter)
        # Create/update column-initial element.
        e = OdtSpan(node, chapter=self.chapter)
        e.sfm_marker = f"\\tc{column_idx}"
        children = p.children
        if len(children) == 0:
            children.append(e)
        elif isinstance(children[0], OdtText):
            e.text = children[0].text
            children[0] = e
        else:
            e.text = ""
            children.insert(0, e)
        self.children.extend(children)
        logging.debug(f"{self.children=}")
