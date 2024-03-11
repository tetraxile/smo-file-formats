# https://zeldamods.org/wiki/BYML

import argparse
import enum
import json
import sys
from util import BinaryReader, ByteOrder, Log

class NodeType(enum.IntEnum):
    STRING = 0xA0
    BINARY = 0xA1
    ARRAY = 0xC0
    HASH = 0xC1
    STRING_TABLE = 0xC2
    BOOL = 0xD0
    I32 = 0xD1
    F32 = 0xD2
    U32 = 0xD3
    I64 = 0xD4
    U64 = 0xD5
    F64 = 0xD6
    NULL = 0xFF


OFFSET_TYPES = (NodeType.BINARY, NodeType.ARRAY, NodeType.HASH,
                NodeType.I64, NodeType.U64, NodeType.F64)

class Header:
    def __init__(self, reader: BinaryReader):
        signature = reader.read_bytes(2)
        reader.byte_order = {b"BY": ByteOrder.big, b"YB": ByteOrder.little}[signature]
        version = reader.read_u16()
        self.hash_key_table_offset = reader.read_u32()
        self.string_table_offset = reader.read_u32()
        self.root_offset = reader.read_u32()


class BYML:
    def __init__(self, stream: bytes, quiet: bool = False):
        self.quiet = quiet
        self.reader = BinaryReader(stream)
        header = Header(self.reader)
        self.cur_node = []

        self.hash_key_table = self.read_string_table(header.hash_key_table_offset)
        self.string_table = self.read_string_table(header.string_table_offset)
        self.root = self.read_root(header.root_offset)

    def get_cur_node(self) -> str:
        cur_node_str = self.cur_node[0]
        for ancestor in self.cur_node[1:]:
            cur_node_str += f"[{ancestor!r}]"
        return cur_node_str

    def get_string(self, idx: int, is_hash_key: bool = False) -> str:
        table = [self.string_table, self.hash_key_table][is_hash_key]
        if table is None:
            Log.error("can't index nonexistent string table")

        try:
            return table[idx]
        except IndexError:
            cur_node = self.get_cur_node()
            Log.error(f"string table index out of range ({cur_node})")

    def read_string_table(self, start: int) -> list[str] | None:
        if start == 0:
            return None

        self.reader.seek(start)
        node_type = NodeType(self.reader.read_u8())
        if node_type != NodeType.STRING_TABLE:
            Log.error(f"expected {NodeType.STRING_TABLE.name}, got {node_type.name}")

        string_count = self.reader.read_u24()
        offsets = self.reader.read_u32s(string_count)

        strings = []
        for offset in offsets:
            self.reader.seek(start + offset)
            strings.append(self.reader.read_string("utf-8"))

        return strings

    def read_root(self, start: int) -> list | dict | None:
        if start == 0:
            return None

        self.cur_node.append("root")

        self.reader.seek(start)
        node_type = NodeType(self.reader.read_u8())
        self.reader.seek(-1, relative=True)

        ctor = {NodeType.ARRAY: self.read_array_node,
                NodeType.HASH: self.read_hash_node}.get(node_type)
        
        if ctor is None:
            Log.error(f"invalid root node type ({node_type.name})")

        root = ctor()
        self.cur_node.pop()
        return root

    def read_string_node(self) -> str:
        idx = self.reader.read_u32()
        return self.get_string(idx)

    def read_binary_node(self) -> bytes:
        length = self.reader.read_u32()
        return self.reader.read_bytes(length)

    def read_array_node(self) -> list:
        node_type = NodeType(self.reader.read_u8())
        if not self.quiet and node_type != NodeType.ARRAY:
            cur_node = self.get_cur_node()
            Log.info(f"hash node type is {node_type.name}, should be ARRAY ({cur_node})")

        entry_count = self.reader.read_u24()
        entry_types = [NodeType(t) for t in self.reader.read_u8s(entry_count)]
        self.reader.align(4)
        entries_start = self.reader.position
        
        entries = []
        for i, entry_type in enumerate(entry_types):
            self.cur_node.append(i)
            self.reader.seek(entries_start + i*4)
            entries.append(self.read_container_entry(entry_type))
            self.cur_node.pop()

        return entries

    def read_hash_node(self) -> dict:
        node_type = NodeType(self.reader.read_u8())
        if not self.quiet and node_type != NodeType.HASH:
            cur_node = self.get_cur_node()
            Log.info(f"hash node type is {node_type.name}, should be HASH ({cur_node})")

        entry_count = self.reader.read_u24()
        entries_start = self.reader.position
        hash = {}
        for i in range(entry_count):
            self.reader.seek(entries_start + i*8)
            name_idx = self.reader.read_u24()
            name = self.get_string(name_idx, is_hash_key=True)

            self.cur_node.append(name)
            entry_type = NodeType(self.reader.read_u8())
            hash[name] = self.read_container_entry(entry_type)
            self.cur_node.pop()

        return hash

    def read_bool_node(self) -> bool:
        value = self.reader.read_u32()
        if value == 0:
            return False
        elif not self.quiet and value != 1:
            cur_node = self.get_cur_node()
            Log.info(f"bool node has value of {value}, should be 0 or 1 ({cur_node})")
        return True

    def read_null_node(self) -> None:
        value = self.reader.read_u32()
        if not self.quiet and value != 0:
            cur_node = self.get_cur_node()
            Log.info(f"null node value is {value}, should be 0 ({cur_node})")
        return None

    def read_container_entry(self, entry_type: NodeType):
        if entry_type in OFFSET_TYPES:
            offset = self.reader.read_u32()
            self.reader.seek(offset)

        ctor = {
            NodeType.STRING: self.read_string_node,
            NodeType.BINARY: self.read_binary_node,
            NodeType.ARRAY: self.read_array_node,
            NodeType.HASH: self.read_hash_node,
            NodeType.BOOL: self.read_bool_node,
            NodeType.I32: self.reader.read_i32,
            NodeType.F32: self.reader.read_f32,
            NodeType.U32: self.reader.read_u32,
            NodeType.I64: self.reader.read_i64,
            NodeType.U64: self.reader.read_u64,
            NodeType.F64: self.reader.read_f64,
            NodeType.NULL: self.read_null_node,
        }[entry_type]

        return ctor()


def main():
    parser = argparse.ArgumentParser(description="read BYML files")
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    with open(args.infile, "rb") as f:
        byml = BYML(f.read(), quiet=args.quiet)

    with open(args.outfile, "w") as f:
        json.dump(byml.root, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
