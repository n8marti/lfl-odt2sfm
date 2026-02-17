import sys

from odfdo import document

d = document.Document(sys.argv[1])
d.save(sys.argv[2])
