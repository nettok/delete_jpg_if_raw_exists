#!/usr/bin/python

import argparse
import os
import fnmatch
import pathlib
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from typing import Optional, FrozenSet


@dataclass
class XmpData:
    rating: Optional[int]
    keywords: FrozenSet[str]


def main():
    parser = argparse.ArgumentParser(description='Deletes photos and sidecar files when they have a negative rating in the DarkTable sidecar XMP file.')
    parser.add_argument('path', type=str, help='The root directory to work on.')
    parser.add_argument('--recursive', action='store_true', help='Traverse directories recursively.')
    parser.add_argument('--delete', action='store_true', help='Delete the photos. By default it just shows the files that would be deleted.')
    
    args = parser.parse_args()

    for path, file in traverse_path(args.path, args.recursive):
        if fnmatch.fnmatch(file, '*.ARW.xmp'):
            process_file(path, file, delete=args.delete)


def traverse_path(path, recursive=False):
    for root, dirs, files in os.walk(path):
        path = root.split(os.sep)
        
        for file in files:
            yield path, file
        
        if not recursive:
            break


def process_file(path, file, delete=False):
    dt_xmp_file_path = pathlib.Path(*path, file)
    moff_file_path = dt_xmp_file_path.with_suffix(".moff")
    c1_xmp_file_path = dt_xmp_file_path.with_suffix("").with_suffix(".xmp")
    photo_file_path = c1_xmp_file_path.with_suffix(".ARW")

    dt_xmp_data = read_dt_xmp_data(dt_xmp_file_path)

    if dt_xmp_data.rating is not None and dt_xmp_data.rating < 0:
        if delete:
            os.remove(dt_xmp_file_path)
            if c1_xmp_file_path.exists():
                os.remove(c1_xmp_file_path)
            if moff_file_path.exists():
                os.remove(moff_file_path)
            if photo_file_path.exists():
                os.remove(photo_file_path)
                print(photo_file_path, "(delete)")
        else:
            print(photo_file_path, "(show)")


def read_dt_xmp_data(path: pathlib.Path):
    tree = ET.parse(path)
    rdf_description = tree.getroot()[0][0]
    
    rating = int(rdf_description.attrib.get("{http://ns.adobe.com/xap/1.0/}Rating"))
    if rating == 1:
        rating = None
    
    subject = rdf_description.find("{http://purl.org/dc/elements/1.1/}subject")
    keywords = frozenset(map(lambda e: e.text, subject[0])) if subject else frozenset()

    return XmpData(rating, keywords)


if __name__ == "__main__":
    main()
