#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2016 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for examining spatial media metadata in MP4/MOV files."""

import os
import re
import struct
import traceback
import xml.etree
import xml.etree.ElementTree
import json

from spatialmedia import mpeg

MPEG_FILE_EXTENSIONS = [".mp4", ".mov"]

SPHERICAL_UUID_ID = (
    b"\xff\xcc\x82\x63\xf8\x55\x4a\x93\x88\x14\x58\x7a\x02\x52\x1f\xdd")

# XML contents.
RDF_PREFIX = " xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\" "

SPHERICAL_XML_HEADER = \
    "<?xml version=\"1.0\"?>"\
    "<rdf:SphericalVideo\n"\
    "xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"\n"\
    "xmlns:GSpherical=\"http://ns.google.com/videos/1.0/spherical/\">"

SPHERICAL_XML_CONTENTS = \
    "<GSpherical:Spherical>true</GSpherical:Spherical>"\
    "<GSpherical:Stitched>true</GSpherical:Stitched>"\
    "<GSpherical:StitchingSoftware>"\
    "Spherical Metadata Tool"\
    "</GSpherical:StitchingSoftware>"\
    "<GSpherical:ProjectionType>equirectangular</GSpherical:ProjectionType>"

SPHERICAL_XML_CONTENTS_TOP_BOTTOM = \
    "<GSpherical:StereoMode>top-bottom</GSpherical:StereoMode>"
SPHERICAL_XML_CONTENTS_LEFT_RIGHT = \
    "<GSpherical:StereoMode>left-right</GSpherical:StereoMode>"

# Parameter order matches that of the crop option.
SPHERICAL_XML_CONTENTS_CROP_FORMAT = \
    "<GSpherical:CroppedAreaImageWidthPixels>{0}"\
    "</GSpherical:CroppedAreaImageWidthPixels>"\
    "<GSpherical:CroppedAreaImageHeightPixels>{1}"\
    "</GSpherical:CroppedAreaImageHeightPixels>"\
    "<GSpherical:FullPanoWidthPixels>{2}</GSpherical:FullPanoWidthPixels>"\
    "<GSpherical:FullPanoHeightPixels>{3}</GSpherical:FullPanoHeightPixels>"\
    "<GSpherical:CroppedAreaLeftPixels>{4}</GSpherical:CroppedAreaLeftPixels>"\
    "<GSpherical:CroppedAreaTopPixels>{5}</GSpherical:CroppedAreaTopPixels>"

SPHERICAL_XML_FOOTER = "</rdf:SphericalVideo>"

SPHERICAL_TAGS_LIST = [
    "Spherical",
    "Stitched",
    "StitchingSoftware",
    "ProjectionType",
    "SourceCount",
    "StereoMode",
    "InitialViewHeadingDegrees",
    "InitialViewPitchDegrees",
    "InitialViewRollDegrees",
    "Timestamp",
    "CroppedAreaImageWidthPixels",
    "CroppedAreaImageHeightPixels",
    "FullPanoWidthPixels",
    "FullPanoHeightPixels",
    "CroppedAreaLeftPixels",
    "CroppedAreaTopPixels",
]

DEFAULT_XML_CONTENTS = """
<rdf:SphericalVideo
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:GSpherical="http://ns.google.com/videos/1.0/spherical/">
  <GSpherical:Spherical>true</GSpherical:Spherical>
  <GSpherical:Stitched>true</GSpherical:Stitched>
  <GSpherical:StitchingSoftware>Unknown</GSpherical:StitchingSoftware>
  <GSpherical:ProjectionType>equirectangular</GSpherical:ProjectionType>
</rdf:SphericalVideo>
"""

class Metadata(object):
    def __init__(self):
        self.video = None

class ParsedMetadata(object):
    def __init__(self):
        self.video = dict()
    def toJson(self):
        full = dict()
        full['video'] = self.video
        return json.dumps(full)

SPHERICAL_PREFIX = "{http://ns.google.com/videos/1.0/spherical/}"
SPHERICAL_TAGS = dict()
for tag in SPHERICAL_TAGS_LIST:
    SPHERICAL_TAGS[SPHERICAL_PREFIX + tag] = tag

integer_regex_group = "(\d+)"
crop_regex = "^{0}$".format(":".join([integer_regex_group] * 6))



def parse_spherical_xml(contents):
    """Returns spherical metadata for a set of xml data.

    Args:
      contents: string, spherical metadata xml contents.

    Returns:
      dictionary containing the parsed spherical metadata values.
    """
    try:
        parsed_xml = xml.etree.ElementTree.XML(contents)
    except xml.etree.ElementTree.ParseError:
        try:
            index = contents.find("<rdf:SphericalVideo")
            if index != -1:
                index += len("<rdf:SphericalVideo")
                contents = contents[:index] + RDF_PREFIX + contents[index:]
            parsed_xml = xml.etree.ElementTree.XML(contents)
        except xml.etree.ElementTree.ParseError as e:
            errorDict = dict()
            errorDict['error'] = 'Invalid XML'
            return errorDict

    sphericalDictionary = dict()
    for child in parsed_xml.getchildren():
        if child.tag in SPHERICAL_TAGS.keys():
            sphericalDictionary[SPHERICAL_TAGS[child.tag]] = child.text
        else:
            tag = child.tag
            if child.tag[:len(spherical_prefix)] == spherical_prefix:
                tag = child.tag[len(spherical_prefix):]

    return sphericalDictionary


def parse_spherical_mpeg4(mpeg4_file, fh):
    """Returns spherical metadata for a loaded mpeg4 file.

    Args:
      mpeg4_file: mpeg4, loaded mpeg4 file contents.
      fh: file handle, file handle for uncached file contents.

    Returns:
      Dictionary stored as (trackName, metadataDictionary)
    """
    metadata = ParsedMetadata()
    track_num = 0
    for element in mpeg4_file.moov_box.contents:
        if element.name == mpeg.constants.TAG_TRAK:
            trackName = "Track %d" % track_num
            track_num += 1
            for sub_element in element.contents:
                if sub_element.name == mpeg.constants.TAG_UUID:
                    if sub_element.contents:
                        sub_element_id = sub_element.contents[:16]
                    else:
                        fh.seek(sub_element.content_start())
                        sub_element_id = fh.read(16)

                    if sub_element_id == SPHERICAL_UUID_ID:
                        if sub_element.contents:
                            contents = sub_element.contents[16:]
                        else:
                            contents = fh.read(sub_element.content_size - 16)
                        if len(contents) == 0:
                            # empty XML. normally from a 360 video processing tool misbehaving Eg. Gear 360 ActionDirector
                            # so just put in default metadata
                            contents = DEFAULT_XML_CONTENTS

                        # I have seen some encodings have invalid starting data (Gear360 ActionDirector)
                        # So when decoding, drop invalid ascii characters
                        metadata.video[trackName] = \
                            parse_spherical_xml(contents.decode("ascii", "ignore"))

    return metadata

def createErrorDict(errMsg):
    result = ParsedMetadata()
    result.video['error'] = dict()
    result.video['error']['error'] = errMsg
    return result

def parse_mpeg4(input_file):
    with open(input_file, "rb") as in_fh:
        mpeg4_file = mpeg.load(in_fh)
        if mpeg4_file is None:
            return createErrorDict('Invalid File')
        return parse_spherical_mpeg4(mpeg4_file, in_fh)

    return createErrorDict('Missing File')

def parse_metadata_structured(src):
    infile = os.path.abspath(src)

    try:
        in_fh = open(infile, "rb")
        in_fh.close()
    except:
        return createErrorDict('No permissions to access file')

    extension = os.path.splitext(infile)[1].lower()

    if extension in MPEG_FILE_EXTENSIONS:
        return parse_mpeg4(infile)

    return createErrorDict('Unknown file type')

def parse_metadata(src):
    result = parse_metadata_structured(src)
    print(result.toJson())

def get_descriptor_length(in_fh):
    """Derives the length of the MP4 elementary stream descriptor at the
       current position in the input file.
    """
    descriptor_length = 0
    for i in range(4):
        size_byte = struct.unpack(">c", in_fh.read(1))[0]
        descriptor_length = (descriptor_length << 7 |
                             ord(size_byte) & int("0x7f", 0))
        if (ord(size_byte) != int("0x80", 0)):
            break
    return descriptor_length
