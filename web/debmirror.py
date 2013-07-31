# Copyright (C) 2013  Stefano Zacchiroli <zack@upsilon.cc>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from debian import deb822
from debian.debian_support import version_compare


class SourcePackage(deb822.Sources):
    """Debian source package, as it appears in a source mirror
    """

    @classmethod
    def from_db_model(cls, db_version):
        """build a (mock) SourcePackage object from a models.Version instance

        note that the build object will not contain all the needed source
        package information, but only those that can be reconstructed using
        information available in the Debsources db.  That, however, should be
        enough for the purposes of Debsources' needs.
        """
        meta = {}
        meta['package'] = db_version.package.name
        meta['version'] = db_version.vnumber
        meta['section'] = db_version.area
        return cls(meta)

    # override deb822's __eq__, as in source package land we can rely on
    # <package, version> pair uniqueness
    def __eq__(self, other):
        """equality based on <package, version> paris only
        """
        if self['package'] != other['package']:
            return False
        if self['version'] != other['version']:
            return False
        return True

    def __cmp__(self, other):
        """comparison based on <package, version> pairs only
        """
        cmp1 = cmp(self['package'], other['package'])
        if cmp1:	# 'package' key is enough to discriminate
            return cmp1
        return version_compare(self['version'], other['version'])

    def __hash__(self):
        """compute hash based on <package, version> pair only
        """
        return hash((self['package'], self['version']))

    def __str__(self):
        """package/version representation of a package
        """
        return "%s/%s" % (self['package'], self['version'])

    __repr__ = __str__
    __unicode__ = __str__

    def archive_area(self):
        """return package are in the debian achive

        one of: main, contrib, non-free
        """
        sec = self['section']
        if sec.startswith('contrib'):
            return 'contrib'
        elif sec.startswith('non-free'):
            return 'non-free'
        else:
            return 'main'

    def prefix(self):
        """compute package prefix in the pool structure

        e.g.: 1st character of package name or "lib" + 1st char, depending on
        the package
        """
        name = self['package']
        if name.startswith('lib'):
            return name[:4]
        else:
            return name[:1]

    def dsc_path(self):
        """return path to .dsc file for this package, relative to mirror root
        """
        dsc = filter(lambda f: f['name'].endswith('.dsc'),
                     self['files'])[0]['name']
        return os.path.join(self['directory'], dsc)

    def extraction_dir(self, basedir=None):
        """return package extraction dir, relative to debsources sources_dir

        if given, prepend basedir path to the generated path
        """
        steps = [ self.archive_area(),
                  self.prefix(),
                  self['package'],
                  self['version'] ]
        if basedir:
            steps.insert(0, basedir)
        return os.path.join(*steps)


def _find_Sources(path):
    """Find Sources.gz entries and return them as <suite, path> pairs
    """
    for root, dirs, files in os.walk(path):
        src_indexes = [ os.path.join(root, file)
                        for file in files
                        if file == "Sources.gz" ]
        for f in src_indexes:
            steps = f.split('/')
            suite = steps[-4]	# wheezy, jessie, sid, ...
            yield suite, f


def ls_mirror(path):
    """List source packages available in a local source mirror

    Return a dictionary mapping (name, version) to SourcePackage instances
    """
    pkgs = {}
    for suite, src_index in _find_Sources(path):
        with open(src_index) as i:
            for pkg in SourcePackage.iter_paragraphs(i):
                pkg_id = (pkg['package'], pkg['version'])
                if pkgs.has_key(pkg_id):
                    pkgs[pkg_id]['x-debsrc-suites'] += ',' + suite
                else:
                    pkg['x-debsrc-suites'] = suite
                    pkgs[pkg_id] = pkg
    return pkgs
