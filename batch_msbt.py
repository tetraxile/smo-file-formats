from msbp import MSBP
from msbt import MSBT
from szs import SZS
import argparse
import json
import os
import sys


def error(message: str):
    print("error: {message}", file=sys.stderr)
    sys.exit(1)


def read_szs_file(path: str) -> SZS:
    with open(path, "rb") as f:
        return SZS(f.read())


def main():
    parser = argparse.ArgumentParser(description="convert all MSBT files to JSON")
    parser.add_argument("romfsdir", help="path to SMO assets")
    parser.add_argument("outdir", help="path to save JSON to")
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    if not os.path.isdir(args.romfsdir):
        error("romfs path doesn't exist")

    if not os.path.isdir(args.outdir):
        error("output path doesn't exist")

    localized_path = f"{args.romfsdir}/LocalizedData"

    if not os.path.isfile(f"{localized_path}/USen/MessageData/StageMessage.szs"):
        error("romfs path doesn't contain LocalizedData")

    szs = read_szs_file(f"{localized_path}/Common/ProjectData.szs")
    msbp = MSBP(szs.files["ProjectData.msbp"])

    languages = filter(lambda k: k != "Common", os.listdir(localized_path))

    for language in languages:
        if not args.quiet:
            print(f"converting {language}...")

        language_path = f"{localized_path}/{language}/MessageData"
        for szs_file in os.listdir(language_path):
            szs_path = f"{language_path}/{szs_file}"
            out_szs_path = f"{args.outdir}/{language}/" + szs_file.removesuffix(".szs")
            os.makedirs(out_szs_path, exist_ok=True)

            szs = read_szs_file(szs_path)
            for filename, data in szs.files.items():
                msbt = MSBT(data, msbp)
                out_path = f"{out_szs_path}/" + filename.removesuffix(".msbt") + ".json"
                with open(out_path, "w") as f:
                    json.dump(msbt.data, f, ensure_ascii=False, indent=2)

    if not args.quiet:
        print("done!")


if __name__ == "__main__":
    main()
