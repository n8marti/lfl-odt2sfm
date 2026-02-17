import sys

from odf import opendocument

d = opendocument.load(sys.argv[1])
d.save(sys.argv[2])
