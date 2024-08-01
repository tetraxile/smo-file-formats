# https://github.com/kinnay/Nintendo-File-Formats/wiki/MSBT-File-Format

import argparse
import json
import lms
from msbp import MSBP
from util import BinaryReader, Log


class LBL1(lms.LabelBlock):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding, _: MSBP):
        super().__init__(reader, encoding)


class TXT2(lms.Block):
    def __init__(self, reader: BinaryReader, encoding: lms.Encoding, project_data: MSBP):
        super().__init__(reader, encoding)
        start = reader.position

        tags = project_data.data["tags"]
        tags[0]["tags"][0]["params"] = [
            {"name": "replace", "type": lms.ParamType.U16},
            {"name": "rt", "type": lms.ParamType.STRING}
        ]
        tags[0]["tags"][2]["params"] = [{"name": "percent", "type": lms.ParamType.U16}]
        tags[0]["tags"][3]["params"] = [{"name": "index", "type": lms.ParamType.I16}]

        message_count = reader.read_u32()
        offsets = reader.read_u32s(message_count)

        self.messages = []
        for offset in offsets:
            reader.seek(start + offset)
            message = self.read_tag_string(reader, tags)
            self.messages.append(message)

    def read_tag_string(self, reader: BinaryReader, tags: dict) -> str:
        char_size, encoding_name = {
            lms.Encoding.UTF8: (1, "utf-8"),
            lms.Encoding.UTF16: (2, "utf-16"),
            lms.Encoding.UTF32: (4, "utf-32")
        }[self.encoding]

        out = ""
        while (char := reader.read(char_size).decode(encoding_name)) != '\x00':
            if char == '\x0e':
                group_idx = reader.read_u16()
                type_idx = reader.read_u16()
                tag_group = tags[group_idx]
                tag = tag_group["tags"][type_idx]

                param_count = reader.read_u16()
                params = []
                for param in tag["params"]:
                    params.append((param["name"], {
                        0: reader.read_u8,
                        1: reader.read_u16,
                        2: reader.read_s16,
                        5: reader.read_u32,
                        6: reader.read_f32,
                        8: lambda: self.read_encoded_string(reader, reader.read_u16()),
                        9: lambda: None,
                    }[param["type"]](), param["type"]))
                
                out_parts = [tag_group["name"], tag["name"]]
                if param_count > 0:
                    out_params = []
                    for name, val, type_ in params:
                        formatted_val = f"'{val}'" if type_ == 8 else f"{val}"
                        out_params.append(f"{name}: {formatted_val}")
                    out_parts.append("(" + ", ".join(out_params) + ")")
                    
                out += "<" + ", ".join(out_parts) + ">"
            else:
                out += char

        return out


class MSBT:
    def __init__(self, stream: bytes, project_data: MSBP):
        reader = BinaryReader(stream)
        header = lms.Header(reader, "MsgStdBn")
        ctors = {"LBL1": LBL1, "TXT2": TXT2}

        self.blocks = {}
        for _ in range(header.num_blocks):
            block_start = reader.position
            signature = reader.read_string("ascii", 4)
            block_size = reader.read_u32()
            reader.read(8) # padding

            if signature in ctors:
                block = ctors[signature](reader, header.encoding, project_data)
                self.blocks[signature] = block
            else:
                Log.error(f"unknown section `{signature}`")

            reader.seek(block_start + block_size + 0x10)
            reader.align(0x10)

        self.data = {}
        if "LBL1" in self.blocks and "TXT2" in self.blocks:
            labels = self.blocks["LBL1"].labels
            messages = self.blocks["TXT2"].messages
            for label in labels:
                self.data[label.name] = messages[label.idx]


def main():
    parser = argparse.ArgumentParser(description="read MSBT message files")
    parser.add_argument("infile")
    parser.add_argument("project_data", help="ProjectData.msbp file")
    parser.add_argument("outfile")
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    with open(args.project_data, "rb") as f:
        project_data = MSBP(f.read())

    with open(args.infile, "rb") as f:
        msbt = MSBT(f.read(), project_data)

    with open(args.outfile, "w") as f:
        json.dump(msbt.data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
