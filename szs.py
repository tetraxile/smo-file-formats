import argparse
from sarc import SARC
from yaz0 import Yaz0

def main():
    parser = argparse.ArgumentParser(description="extract SZS archives")
    parser.add_argument("infile")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("outdir")

    args = parser.parse_args()

    uncompressed = Yaz0.decompress_file(args.infile)
    sarc = SARC(uncompressed)
    sarc.save(args.outdir, quiet=args.quiet)


if __name__ == "__main__":
    main()
