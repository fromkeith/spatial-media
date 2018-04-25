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
"""Spatial Media Metadata Injector 

Tool for examining and injecting spatial media metadata in MP4/MOV files.
"""

import argparse
import os
import re
import sys

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)
from spatialmedia import metadata_utils


def main():
  """Main function for printing and injecting spatial media metadata."""

  parser = argparse.ArgumentParser(
      usage=
      "%(prog)s [file]\n\nBy default prints out spatial media "
      "metadata from specified files.")
  parser.add_argument("file", help="input file")

  args = parser.parse_args()

  if len(args.file) > 0:
    metadata_utils.parse_metadata(args.file)
    return

  parser.print_help()
  return


if __name__ == "__main__":
  main()
