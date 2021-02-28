#!/usr/bin/python

import argparse
import os
import fnmatch
import pathlib


def main():
    parser = argparse.ArgumentParser(description='Delete orphan XMP files.')
    parser.add_argument('path', type=str, help='The root directory to work on.')
    parser.add_argument('--recursive', action='store_true', help='Traverse directories recursively.')
    parser.add_argument('--delete', action='store_true', help='Do delete the XMP files. By default it just shows the files that would be deleted.')
    
    args = parser.parse_args()

    for path, file in traverse_path(args.path, args.recursive):
        if fnmatch.fnmatch(file, '*.xmp'):
            process_file(path, file, delete=args.delete)


def traverse_path(path, recursive=False):
    for root, dirs, files in os.walk(path):
        path = root.split(os.sep)
        
        for file in files:
            yield path, file
        
        if not recursive:
            break


def process_file(path, file, delete=False):
    xmp_file_path = pathlib.Path(*path, file)
    derived_from_file_path = xmp_file_path.with_suffix("")

    if derived_from_file_path.suffix and not derived_from_file_path.exists():
        if delete:
            os.remove(xmp_file_path)
            print(xmp_file_path, '(delete)')
        else:
            print(xmp_file_path, '(show)')


if __name__ == "__main__":
    main()
