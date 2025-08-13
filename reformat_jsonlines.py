from utils import parse_json_objects
import sys
import json

def main():
    input_file = sys.argv[1]
    # parse JSON objects from the input file
    # and write them in jsonlines format to stdout

    objects = parse_json_objects(input_file)
    for obj in objects:
        print(json.dumps(obj, ensure_ascii=False))

if __name__ == "__main__":
    main()