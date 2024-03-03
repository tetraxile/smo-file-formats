import argparse
import yaz0
from sarc import SARC


class SZS:
    def __init__(self, stream: bytes):
        uncompressed = yaz0.decompress(stream)
        self._sarc = SARC(uncompressed)

    def save(self, outdir: str, quiet: bool = True):
        self._sarc.save(outdir, quiet=quiet)

    @property
    def files(self):
        return self._sarc.files


def main():
    parser = argparse.ArgumentParser(description="extract SZS archives")
    parser.add_argument("infile")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("outdir")

    args = parser.parse_args()

    with open(args.infile, "rb") as f:
        szs = SZS(f.read())

    szs.save(args.outdir, quiet=args.quiet)


if __name__ == "__main__":
    main()
