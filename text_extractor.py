import json
import pathlib
import sys

from PIL import Image
import pytesseract


def extract_text_from_file(path: str) -> dict:
    p = pathlib.Path(path)
    filename = p.stem
    filetype = p.suffix[1:]

    text = ""

    try:
        image = Image.open(path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        print(f"[ERROR] Error processing {path}: {e}", file=sys.stderr)

    return {
        "filename": filename,
        "filetype": filetype,
        "text": text,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python text_extractor.py /path/to/image")
        return

    result = extract_text_from_file(sys.argv[1])

    output = json.dumps(result, indent=4, ensure_ascii=False)
    return output


if __name__ == "__main__":
    main()
