# https://github.com/kinnay/Nintendo-File-Formats/wiki/MSBP-File-Format

import argparse
import json
import lms
from util import BinaryReader


class CLR1(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        color_count = reader.read_u32()
        self.colors = []
        for _ in range(color_count):
            color = tuple(reader.read_u8() for _ in range(4))
            color = "0x" + "".join(f"{c:02x}" for c in color)
            self.colors.append(color)


class ATI2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)

        attr_count = reader.read_u32()
        self.attrs = []

        for _ in range(attr_count):
            attr_type = reader.read_u8()
            reader.read_u8() # padding
            attr_idx = reader.read_u16()
            attr_offset = reader.read_u32()
            self.attrs.append((attr_type, attr_idx, attr_offset))


class ALI2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        list_count = reader.read_u32()
        offsets = reader.read_u32s(list_count)

        self.attr_lists = []
        for offset in offsets:
            reader.seek(start + offset)
            attr_list = []
            item_count = reader.read_u32()
            name_offsets = reader.read_u32s(item_count)
            for name_offset in name_offsets:
                reader.seek(start + name_offset)
                name = self.read_encoded_string(reader)
                attr_list.append(name)
            self.attr_lists.append(attr_list)


class TGG2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        group_count = reader.read_u16()
        reader.read_u16() # padding
        offsets = reader.read_u32s(group_count)

        self.groups = []
        for offset in offsets:
            reader.seek(start + offset)
            group_idx = reader.read_u16()
            tag_count = reader.read_u16()
            tag_indices = reader.read_u16s(tag_count)
            group_name = self.read_encoded_string(reader)
            self.groups.append((group_idx, group_name, tag_indices))


class TAG2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        tag_count = reader.read_u16()
        reader.read_u16() # padding
        offsets = reader.read_u32s(tag_count)

        self.tags = []
        for offset in offsets:
            reader.seek(start + offset)
            param_count = reader.read_u16()
            params = reader.read_u16s(param_count)
            tag_name = self.read_encoded_string(reader)
            self.tags.append((tag_name, params))


class TGP2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        param_count = reader.read_u16()
        reader.read_u16() # padding
        offsets = reader.read_u32s(param_count)

        self.params = []
        for offset in offsets:
            reader.seek(start + offset)
            param_type = reader.read_u8()
            if param_type == lms.ParamType.NULL:
                reader.read_u8() # padding
                item_count = reader.read_u16()
                items = reader.read_u16s(item_count)
                param_name = self.read_encoded_string(reader)
                self.params.append((param_type, param_name, items))
            else:
                param_name = self.read_encoded_string(reader)
                self.params.append((param_type, param_name))


class TGL2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        item_count = reader.read_u16()
        reader.read_u16() # padding
        offsets = reader.read_u32s(item_count)

        self.items = []
        for offset in offsets:
            reader.seek(start + offset)
            item_name = self.read_encoded_string(reader)
            self.items.append(item_name)


class SYL3(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        
        style_count = reader.read_u32()
        self.styles = []
        for _ in range(style_count):
            region_width = reader.read_u32()
            line_num = reader.read_u32()
            font_idx = reader.read_u32()
            base_color_idx = reader.read_i32()
            self.styles.append((region_width, line_num, font_idx, base_color_idx))


class CTI1(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding):
        super().__init__(reader, encoding)
        start = reader.position

        filename_count = reader.read_u32()
        offsets = reader.read_u32s(filename_count)

        self.filenames = []
        for offset in offsets:
            reader.seek(start + offset)
            self.filenames.append(self.read_encoded_string(reader))


class MSBP:
    def __init__(self, stream: bytes):
        reader = BinaryReader(stream)
        header = lms.Header(reader, "MsgPrjBn")
        ctors = {
            "CLR1": CLR1, "ATI2": ATI2, "ALI2": ALI2,
            "TGG2": TGG2, "TAG2": TAG2, "TGP2": TGP2,
            "TGL2": TGL2, "SYL3": SYL3, "CTI1": CTI1,
            "CLB1": lms.LabelBlock, "ALB1": lms.LabelBlock,
            "SLB1": lms.LabelBlock
        }

        self.blocks = {}
        for _ in range(header.num_blocks):
            block_start = reader.position
            signature = reader.read_string("ascii", 4)
            block_size = reader.read_u32()
            reader.read(8) # padding

            if signature in ctors:
                block = ctors[signature](reader, header.encoding)
                self.blocks[signature] = block
            else:
                raise NotImplementedError(f"unknown section `{signature}`")
            
            reader.seek(block_start + block_size + 0x10)
            reader.align(0x10)

        self.data = {}

        # colors
        color_blocks = ("CLR1", "CLB1")
        if all(block in self.blocks for block in color_blocks):
            self.data["colors"] = {}
            colors = self.blocks["CLR1"].colors
            for label in self.blocks["CLB1"].labels:
                self.data["colors"][label.name] =  colors[label.idx]

        # attributes
        attr_blocks = ("ATI2", "ALB1", "ALI2")
        if all(block in self.blocks for block in attr_blocks):
            raise NotImplementedError("unused in odyssey")

        # tags
        tag_blocks = ("TGG2", "TAG2", "TGP2", "TGL2")
        if all(block in self.blocks for block in tag_blocks):
            self.data["tags"] = {}
            groups = self.blocks["TGG2"].groups
            tags = self.blocks["TAG2"].tags
            params = self.blocks["TGP2"].params
            
            for group_idx, group_name, group_tags in groups:
                group = {"name": group_name, "tags": []}
                for tag_idx in group_tags:
                    tag_name, tag_params = tags[tag_idx]
                    tag = {"name": tag_name, "params": []}
                    for param_idx in tag_params:
                        param_type, param_name = params[param_idx]
                        param = {"name": param_name, "type": param_type}
                        tag["params"].append(param)
                    group["tags"].append(tag)
                self.data["tags"][group_idx] = group

        # styles
        style_blocks = ("SYL3", "SLB1")
        if all(block in self.blocks for block in style_blocks):
            self.data["styles"] = {}
            styles = self.blocks["SYL3"].styles
            for label in self.blocks["SLB1"].labels:
                self.data["styles"][label.name] = styles[label.idx]

        # filenames
        if "CTI1" in self.blocks:
            self.data["filenames"] = self.blocks["CTI1"].filenames


def main():
    parser = argparse.ArgumentParser(description="read MSBP project files")
    parser.add_argument("infile")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("outfile", help="output as JSON")

    args = parser.parse_args()

    with open(args.infile, "rb") as f:
        msbp = MSBP(f.read())

    with open(args.outfile, "w") as f:
        json.dump(msbp.data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
