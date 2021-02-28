#!/usr/bin/python

import argparse
import os
import fnmatch
import pathlib
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from typing import Optional, FrozenSet
from enum import Enum


@dataclass
class XmpData:
    rating: Optional[int]
    keywords: FrozenSet[str]


class RequiresMigration(Enum):
    YES = 1
    NO = 2
    CONFLICT = 3
    MERGE = 4


def main():
    parser = argparse.ArgumentParser(description='Migrates rating and keyword/tag information from DarkTable generated *.ARW.xmp files, to CaptureOne generated *.xmp files.')
    parser.add_argument('path', type=str, help='The root directory to work on.')
    parser.add_argument('--recursive', action='store_true', help='Traverse directories recursively.')
    parser.add_argument('--migrate', action='store_true', help='Do write the migrated information to the XMP files. By default it just shows the files and data that would be migrated.')
    
    args = parser.parse_args()

    for path, file in traverse_path(args.path, args.recursive):
        if fnmatch.fnmatch(file, '*.ARW.xmp'):
            process_file(path, file, migrate=args.migrate)


def traverse_path(path, recursive=False):
    for root, dirs, files in os.walk(path):
        path = root.split(os.sep)
        
        for file in files:
            yield path, file
        
        if not recursive:
            break


def process_file(path, file, migrate=False):
    dt_xmp_file_path = pathlib.Path(*path, file)
    c1_xmp_file_path = dt_xmp_file_path.with_suffix("").with_suffix(".xmp")

    if not c1_xmp_file_path.exists():
        print("warning: Capture One sidecar file does not exists:", c1_xmp_file_path)
        return

    dt_xmp_data = read_dt_xmp_data(dt_xmp_file_path)
    c1_xmp_data = read_c1_xmp_data(c1_xmp_file_path)

    requires_migration = check_requires_migration(dt_xmp_data, c1_xmp_data)
    if requires_migration is not RequiresMigration.YES:
        if requires_migration is RequiresMigration.CONFLICT:
            print(str(c1_xmp_file_path) + ":", dt_xmp_data, "-", c1_xmp_data, "(conflict)")
        return

    if migrate:
        do_migrate(dt_xmp_data, c1_xmp_data, c1_xmp_file_path)
        print(str(c1_xmp_file_path) + ":", dt_xmp_data, "-", c1_xmp_data, "(migrate)" + (" (merge)" if requires_migration is RequiresMigration.MERGE else ""))
    else:
        print(str(c1_xmp_file_path) + ":", dt_xmp_data, "-", c1_xmp_data, "(show)" + (" (merge)" if requires_migration is RequiresMigration.MERGE else ""))


def read_dt_xmp_data(path: pathlib.Path):
    tree = ET.parse(path)
    rdf_description = tree.getroot()[0][0]
    
    rating = int(rdf_description.attrib.get("{http://ns.adobe.com/xap/1.0/}Rating"))
    if rating == 1:
        rating = None
    
    subject = rdf_description.find("{http://purl.org/dc/elements/1.1/}subject")
    keywords = frozenset(map(lambda e: e.text, subject[0])) if subject else frozenset()

    return XmpData(rating, keywords)


def read_c1_xmp_data(path: pathlib.Path):
    tree = ET.parse(path)
    rdf_description = tree.getroot()[0][0]
    
    rating = rdf_description.find("{http://ns.adobe.com/xap/1.0/}Rating")
    rating = int(rating.text) if rating is not None else None
    
    subject = rdf_description.find("{http://purl.org/dc/elements/1.1/}subject")
    keywords = frozenset(map(lambda e: e.text, subject[0])) if subject else frozenset()

    return XmpData(rating, keywords)


def check_requires_migration(dt: XmpData, c1: XmpData) -> RequiresMigration:
    """It is more interesting to know if there are rating CONFLICTs or keywords require a MERGE, so those variants are prioritized as a result."""
    if dt.rating is not None and c1.rating is not None:
        if dt.rating != c1.rating:
            return RequiresMigration.CONFLICT
    
    if dt.keywords - c1.keywords:
        if c1.keywords:
            return RequiresMigration.MERGE
        else:
            return RequiresMigration.YES
    
    if dt.rating is not None and c1.rating is None:
            return RequiresMigration.YES

    return RequiresMigration.NO


def do_migrate(dt: XmpData, c1: XmpData, c1_xmp_file_path: pathlib.Path):
    content = c1_xmp_file_path.read_text()
    content = do_migrate_rating(dt, c1, content)
    content = do_migrate_keywords(dt, c1, content)
    c1_xmp_file_path.write_text(content)


def do_migrate_rating(dt: XmpData, c1: XmpData, content: str) -> str:
    if dt.rating is None or c1.rating is not None:
        return content

    content_lines = content.splitlines()
    insert_index = content_lines.index("  </rdf:Description>")
    content_lines.insert(insert_index, f"   <xmp:Rating>{dt.rating}</xmp:Rating>")

    return '\n'.join(content_lines)


def do_migrate_keywords(dt: XmpData, c1: XmpData, content: str) -> str:
    new_keywords = dt.keywords - c1.keywords
    if not new_keywords:
        return content

    keywords = dt.keywords.union(c1.keywords)

    keywords_lines = '\n'.join([f"     <rdf:li>{kw}</rdf:li>" for kw in keywords])
    
    new_lines =  "   <dc:subject>\n    <rdf:Bag>"
    new_lines += keywords_lines
    new_lines += "    </rdf:Bag>\n   </dc:subject>"
    new_lines =  "   <lightroom:hierarchicalSubject>\n    <rdf:Bag>"
    new_lines += keywords_lines
    new_lines += "    </rdf:Bag>\n   </lightroom:hierarchicalSubject>"

    content_lines = content.splitlines()
    
    if check_requires_migration(dt, c1) is RequiresMigration.MERGE:
        delete_start_index = content_lines.index("   <dc:subject>")
        delete_end_index = content_lines.index("   </dc:subject>")
        for _ in range(delete_end_index - delete_start_index + 1):
            content_lines.pop(delete_start_index)

        delete_start_index = content_lines.index("   <lightroom:hierarchicalSubject>")
        delete_end_index = content_lines.index("   </lightroom:hierarchicalSubject>")
        for _ in range(delete_end_index - delete_start_index + 1):
            content_lines.pop(delete_start_index)

    insert_index = content_lines.index("  </rdf:Description>")
    content_lines.insert(insert_index, new_lines)

    return '\n'.join(content_lines)


if __name__ == "__main__":
    main()
