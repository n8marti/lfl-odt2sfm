import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from odt2sfm.conversions import OdtToSfm, SfmToOdt


def parse_args():
    prog = "odt2sfm"
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="use debug output in log file",
    )
    parser.add_argument("source_path", type=Path, help="source file/dir")
    parser.add_argument("destination_path", type=Path, help="destination file/dir")
    return parser.parse_args()


def main():
    # Get args.
    args = parse_args()

    # Set loglevel for logfile.
    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # Evaluate path args.
    if args.source_path.suffix.lower() == ".sfm":
        conv = SfmToOdt
    elif args.source_path.is_dir():
        logger_filepath = args.source_path / "odt2sfm.log"
        conv = OdtToSfm
    else:
        raise ValueError(f"Invalid source: {args.source_path}")

    if conv is SfmToOdt:
        if not args.destination_path.is_dir():
            raise ValueError(
                f"{conv} conversion requires a destination dir containing ODT files."
            )
        logger_filepath = args.destination_path / "odt2sfm.log"

    # Add file handler to logger and remove console logger.
    logfile_handler = logging.FileHandler(logger_filepath)
    logfile_handler.setFormatter(logger.handlers[0].formatter)  # use console formatter
    logger_filepath.write_text("")  # truncate the file
    logger.addHandler(logfile_handler)
    logger.removeHandler(logger.handlers[0])
    logging.info(f"Script start time: {datetime.now()}")

    # Run converion.
    c = conv(source=args.source_path, destination=args.destination_path)
    c.run()


if __name__ == "__main__":
    main()
