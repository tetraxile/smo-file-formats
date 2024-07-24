# https://mk8.tockdom.com/wiki/SARC_(File_Format)

import argparse
import os
from util import BinaryReader, Log


class Header:
    def __init__(self, reader: BinaryReader):
        reader.read_signature(4, "SARC")
        assert reader.read_u16() == 0x14 # header size
        reader.read_byte_order()
        self.file_size = reader.read_u32()
        self.data_offset = reader.read_u32()
        version = reader.read_u16()
        reader.read(2) # reserved

# SARC File Allocation Table
# specifies the start and end offsets of each file's data
class SFAT:
    class Entry:
        def __init__(self, reader: BinaryReader):
            self.filename_hash = reader.read_u32()
            self.file_attributes = reader.read_u32()
            self.start_offset = reader.read_u32()
            self.end_offset = reader.read_u32()

    def __init__(self, reader: BinaryReader):
        reader.read_signature(4, "SFAT")
        assert reader.read_u16() == 0xc, "SFAT entries offset"
        self.file_count = reader.read_u16()
        hash_key = reader.read_u32()

        self.files = [self.Entry(reader) for _ in range(self.file_count)]

# SARC File Name Table
# specifies the name of each file
class SFNT:
    def __init__(self, reader: BinaryReader, count: int):
        reader.read_signature(4, "SFNT")
        assert reader.read_u16() == 0x8, "SFNT filenames offset"
        reader.read(2) # reserved
        
        self.filenames = []
        for _ in range(count):
            self.filenames.append(reader.read_string("utf-8"))
            reader.align(4)


class SARC:
    def __init__(self, stream: bytes):
        reader = BinaryReader(stream)
        header = Header(reader)
        sfat = SFAT(reader)
        sfnt = SFNT(reader, sfat.file_count)

        self.files = {}
        for file, filename in zip(sfat.files, sfnt.filenames):
            start = header.data_offset + file.start_offset
            length = file.end_offset - file.start_offset
            reader.seek(start)
            file_data = reader.read(length)

            self.files[filename] = file_data

    def save(self, outdir: str, quiet: bool = True):
        os.mkdir(outdir)

        for filename, file in self.files.items():
            path = os.path.join(outdir, filename)

            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path), exist_ok=True)

            if not quiet:
                Log.info(f"saved {path}")

                with open(path, "wb") as f:
                    f.write(file)


def main():
    parser = argparse.ArgumentParser(description="extract SARC archives")
    parser.add_argument("infile")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("outdir")

    args = parser.parse_args()

    with open(args.infile, "rb") as f:
        sarc = SARC(f.read())

    sarc.save(args.outdir, quiet=args.quiet)


if __name__ == "__main__":
    main()
