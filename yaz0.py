# http://www.amnoid.de/gc/yaz0.txt

import argparse
import os
import struct
import sys

class Yaz0:
    @staticmethod
    def decompress(src: bytes) -> bytes:
        signature = src[:4]
        if signature != b'Yaz0':
            print(f"error: file signature was {signature}, expected {b'Yaz0'}", file=sys.stderr)
            sys.exit(1)

        uncompressed_size, = struct.unpack(">I", src[4:8])

        data = src[0x10:]

        dst_buffer = bytearray(uncompressed_size)

        src_idx = 0
        dst_idx = 0
        code_bit_count = 0
        code_byte = 0

        while dst_idx < uncompressed_size:
            if code_bit_count == 0:
                code_byte = data[src_idx]
                src_idx += 1
                code_bit_count = 8
            
            if (code_byte & 0x80) != 0:
                # straight copy
                dst_buffer[dst_idx] = data[src_idx]
                dst_idx += 1
                src_idx += 1
            
            else:
                # LZMA copy
                byte1 = data[src_idx]
                byte2 = data[src_idx + 1]
                src_idx += 2

                dist = ((byte1 & 0xf) << 8) | byte2
                copy_idx = dst_idx - (dist + 1)

                num_bytes = byte1 >> 4
                if num_bytes == 0:
                    num_bytes = data[src_idx] + 0x12
                    src_idx += 1
                else:
                    num_bytes += 2
                
                for _ in range(num_bytes):
                    dst_buffer[dst_idx] = dst_buffer[copy_idx]
                    copy_idx += 1
                    dst_idx += 1
            
            code_byte <<= 1
            code_bit_count -= 1
        
        return bytes(dst_buffer)

    @staticmethod
    def decompress_file(filename: str) -> bytes:
        if not os.path.isfile(filename):
            print(f"error: input file {filename} does not exist", file=sys.stderr)
            sys.exit(1)

        with open(filename, "rb") as f:
            return Yaz0.decompress(f.read())

    
def main():
    parser = argparse.ArgumentParser(description="decompress Yaz0 compressed files")
    parser.add_argument("infile")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("outfile")

    args = parser.parse_args()

    uncompressed = Yaz0.decompress_file(args.infile)

    with open(args.outfile, "wb") as f:
        f.write(uncompressed)


if __name__ == "__main__":
    main()
