import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from odt2sfm.conversions import SfmToOdt


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    # logging.getLogger().setLevel(logging.WARNING)
    conv = SfmToOdt(source=sys.argv[1], destination=sys.argv[2])
    conv.run()


if __name__ == "__main__":
    main()
