import enum
from util import BinaryReader


class Encoding(enum.IntEnum):
    UTF8 = 0
    UTF16 = 1
    UTF32 = 2


class ParamType(enum.IntEnum):
    U8 = 0
    U16 = 1
    I16 = 2
    U32 = 5
    F32 = 6
    STRING = 8
    NULL = 9


class Header:
    def __init__(self, reader: BinaryReader, signature: str):
        reader.read_signature(8, signature)
        reader.read_byte_order()
        reader.read(2) # unknown (always 0?)
        self.encoding = Encoding(reader.read_u8())
        self.version = reader.read_u8()
        self.num_blocks = reader.read_u16()
        reader.read(2) # unknown (always 0?)
        self.file_size = reader.read_u32()
        reader.read(10) # padding


class Block:
    def __init__(self, _: BinaryReader, encoding: Encoding):
        self.encoding = encoding

    def read_encoded_string(self, reader: BinaryReader, size: int = -1) -> str:
        char_size, encoding_name = {
            Encoding.UTF8: (1, "utf-8"),
            Encoding.UTF16: (2, "utf-16"),
            Encoding.UTF32: (4, "utf-32"),
        }[self.encoding]

        return reader.read_string(encoding_name, size, char_size)


class LabelBlock(Block):
    class Group:
        def __init__(self, reader: BinaryReader):
            self.label_count = reader.read_u32()
            self.offset = reader.read_u32()

    class Label:
        def __init__(self, reader: BinaryReader):
            length = reader.read_u8()
            self.name = reader.read_string("utf-8", length)
            self.idx = reader.read_u32()

    def __init__(self, reader: BinaryReader, encoding: Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        group_count = reader.read_u32()
        groups = [self.Group(reader) for _ in range(group_count)]

        self.labels = []
        for group in groups:
            reader.seek(start + group.offset)
            for _ in range(group.label_count):
                label = self.Label(reader)
                self.labels.append(label)

        self.labels.sort(key=lambda k: k.idx)
