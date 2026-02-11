import sys
from odf.opendocument import load
from odf import text
from pathlib import Path


def show_content(content, all=False):
    t_last = ""
    for k, v in content.items():
        s, t = v
        # Skip duplicated "English translation" paragraphs.
        if "english_20_translation" in s.lower():
            continue
        if not all:
            # Skip paragraphs whose text is identical to the previous paragraph.
            if str(t) == str(t_last):
                continue
        t_last = t
        print(f"{k:2d}: [{s}] {t}")


def main():
    infile = Path(sys.argv[1])
    doc = load(infile)
    content = dict()
    # styles_to_convert = list()
    for i, p in enumerate(doc.getElementsByType(text.P)):
        content[i] = (str(p.getAttribute("stylename")), p)
        show_content(content, all=True)
        # if s not in styles_to_convert:
        #     styles_to_convert.append(s)

    # Save styles list to text file.
    # outfile = Path("ref.txt")
    # outfile.write_text(f"{'\n'.join(styles_to_convert)}")


if __name__ == "__main__":
    main()
