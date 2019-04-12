# Copyright (c) 2017 Nuvadga Christian. All rights reserved.
# https://github.com/spdx/license-coverage-grader/
# The License-Coverage-Grader software is licensed under the Apache License version 2.0.
# Data generated with license-coverage-grader require an acknowledgment.
# license-coverage-grader is a trademark of The Software Package Data
# Exchange(SPDX).

# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

# When you publish or redistribute any data created with license-coverage-grader or any license-coverage-grader
# derivative work, you must accompany this data with the following
# acknowledgment:

#   Generated with license-coverage-grader and provided on an "AS IS" BASIS, WITHOUT WARRANTIES
#   OR CONDITIONS OF ANY KIND, either express or implied.

#!/usr/bin/python

from __future__ import print_function
from argparse import ArgumentParser

import Levenshtein as lev
import copy
import sys
import csv


class spdxdata(object):
    def __init__(self, fname):
        self.fname = fname
        self.parser = ""
        self.filerefs = {}
        self.files = set()


class filedata(object):
    def __init__(self, fname, info=None, concluded=None):
        self.fname = fname
        self.licinfo = []
        self.licconcluded = []
        if info:
            self.licinfo.append(info)
        if concluded:
            self.licconcluded.append(concluded)

# Trivial SPDX scan


def read_spdx(filename, spdx):
    with open(filename) as f:
        fname = None
        for line in f.readlines():

            parts = line.split(":", 1)
            key = parts[0].strip()

            if key == 'Creator':
                parts = line.split(":", 2)
                if parts[1].strip() == 'Tool':
                    spdx.parser = parts[2].strip()

            if key == 'FileName':
                if (fname):
                    spdx.filerefs[fname] = fdata

                fname = parts[1].strip().split(
                    '/', 1)[1].strip().replace(",", "%2C")
                fdata = filedata(fname)

            if key == 'LicenseConcluded':
                lic = parts[1].strip()
                if lic == 'NONE':
                    lic = 'NOASSERTION'
                if lic not in fdata.licconcluded:
                    fdata.licconcluded.append(lic)

            if key == 'LicenseInfoInFile':
                lic = parts[1].strip()
                if lic == 'NONE':
                    lic = 'NOASSERTION'
                if lic not in fdata.licinfo:
                    fdata.licinfo.append(lic)
        if fname:
            spdx.filerefs[fname] = fdata

# LID CSV scan


def read_csv(filename, spdx):

    spdx.parser = 'LID'

    with open(filename) as f:
        rdr = csv.reader(f)
        i = 0

        for row in rdr:
            i += 1
            if i == 1:
                continue

            fn = row[0].split('/', 1)[1].strip().replace(",", "%2C")
            lic = row[1]

            fd = spdx.filerefs.pop(fn, filedata(fn))
            if lic not in fd.licinfo:
                fd.licinfo.append(lic)
            spdx.filerefs[fn] = fd


def diff_spdx(spdxfiles, totfiles, wr):

    spdx = {}
    files = set()

    t = "Tool %d" % totfiles
    for spf in spdxfiles:
        s = spdxdata(spf)

        if spf.endswith(".spdx"):
            read_spdx(spf, s)
        else:
            read_csv(spf, s)

        s.files = set(sorted(s.filerefs.keys()))
        files = files | s.files
        spdx[spf] = s
        t += "," + s.parser + ":%d" % (len(s.files))

    t += ",Match"

    print(t)

    if wr:
        # Sanitize wr output which drops '/'
        # from the middle of the file path
        #
        # Are there any functional tools out there?
        #
        # This certainly can be done smarter, but WTF
        sanitize = {}
        for src in sorted(files):
            if src in sanitize:
                continue
            for crap in sorted(files):
                if crap in sanitize:
                    continue

                if len(src) - len(crap) != 1:
                    continue

                ops = lev.opcodes(src, crap)
                if len(ops) != 3:
                    continue

                # arch/arc/cpu/arc700/u-boot.lds -> arch/arc/cpu/arc700u-boot.lds
                #[('equal', 0, 19, 0, 19), ('delete', 19, 20, 19, 19), ('equal', 20, 30, 19, 29)]
                if ops[0][0] != 'equal' or ops[1][0] != 'delete' or ops[2][0] != 'equal':
                    continue
                if ops[1][1] != ops[1][3] or ops[1][1] != ops[1][4]:
                    continue
                if ops[1][2] - ops[1][1] != 1:
                    continue
                if src[ops[1][1]] != '/':
                    continue

                sanitize[crap] = src

            files = set()
            sanset = set(sanitize.keys())
            for spf in spdxfiles:
                s = spdx[spf]
                for crap in sanset & s.files:
                    ref = s.filerefs.pop(crap)
                    src = sanitize[crap]
                    ref.fname = src
                    s.filerefs[src] = ref
                s.files = set(sorted(s.filerefs.keys()))
                files = files | s.files
    for src in sorted(files):
        info = src
        lics = None
        match = "Y"
        for spf in spdxfiles:
            l = spdx[spf].filerefs.get(src, filedata(
                src, 'NOTSCANNED', 'NOTSCANNED')).licinfo
            lico = spdx[spf].filerefs.get(src, filedata(
                src, 'NOTSCANNED', 'NOTSCANNED')).licconcluded
            if not lics:
                lics = copy.copy(l)
            elif set(lics) != set(l):
                match = "N"
            if not lics:
                lics = copy.copy(lico)
            elif set(lics) != set(lico):
                match = "N"
            info = "," + " ".join(map(str, l)) + "," + " ".join(map(str, lico))
        print(src + info)


if __name__ == '__main__':
    parser = ArgumentParser(description='Diff of two or more SPDX files')
    parser.add_argument('filenames', metavar='file', nargs='+',
                        help='list of source URIs, minimum 2')
    parser.add_argument("-s", "--sourcefiles", type=int, default=0,
                        help="Number of files in the source")
    parser.add_argument("-w", "--wr", action='store_true',
                        help="Sanitize wr filenames")

    args = parser.parse_args()

    if len(args.filenames) < 1:
        print("Not enough SPDX files\n")
        sys.exit(1)

    diff_spdx(args.filenames, args.sourcefiles, args.wr)
