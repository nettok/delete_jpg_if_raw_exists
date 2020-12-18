#!/usr/bin/python

import argparse
import os
import fnmatch
import pathlib


def main():
    parser = argparse.ArgumentParser(description='Delete JPG files if equivalent ARW file exists.')
    parser.add_argument('path', type=str, help='The root directory to work on.')
    parser.add_argument('--recursive', action='store_true', help='Traverse directories recursively.')
    parser.add_argument('--delete', action='store_true', help='Do delete the JPG files. By defauly it just shows the files that would be deleted.')
    
    args = parser.parse_args()

    for path, file in traverse_path(args.path, args.recursive):
        if fnmatch.fnmatch(file, '*.arw'):
            process_file(path, file, delete_jpg=args.delete)


def traverse_path(path, recursive=False):
    for root, dirs, files in os.walk(path):
        path = root.split(os.sep)
        
        for file in files:
            yield path, file
        
        if not recursive:
            break


def process_file(path, file, delete_jpg=False):
    raw_file_path = pathlib.Path(*path, file)
    jpg_file_path = raw_file_path.with_suffix('.jpg')
    
    if (jpg_file_path.exists()):
        if delete_jpg:
            os.remove(jpg_file_path)
            print(jpg_file_path, '(delete)')
        else:
            print(jpg_file_path, '(show)')


if __name__ == "__main__":
    main()
