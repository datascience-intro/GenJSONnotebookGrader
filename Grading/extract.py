import argparse
import json


def output_location(dir_name, file_name, ext="html"):
    return "%s/%s.%s" % (dir_name, file_name, ext)


def extract_content(input_file, output_dir):
    with open(input_file, 'r') as reader:
        exported_content = reader.read()

    data = json.loads(exported_content).get("views")
    output_file_names = set()
    for element in data:
        if element.get("type", None).lower() != "notebook":
            continue
        output_file = element.get("name")
        counter = 0
        while output_file in output_file_names:
            counter += 1
            output_file = "%s_%d" % (output_file, counter)
        output_file_names.add(output_file)
        with open(output_location(output_dir, output_file), "w") as writer:
            writer.write(str(element.get("content", "")))
    print(", ".join([output_location(output_dir, f) for f in output_file_names]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file',
                        help='Path to file containing output of run export.',
                        required=True)
    parser.add_argument('--output_dir',
                        help="Path to directory where extracted HTML pages are to be saved.",
                        required=True)

    args = parser.parse_args()
    extract_content(args.input_file, args.output_dir)
