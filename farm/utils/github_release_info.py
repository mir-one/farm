# -*- coding: utf-8 -*-
import argparse
import json
import logging
import sys
from urllib.request import Request
from urllib.request import urlopen

import os
import re
from pkg_resources import parse_version

sys.path.append(
    os.path.abspath(os.path.join(
        os.path.dirname(__file__), os.path.pardir) + '/..'))

from farm.config import FARM_VERSION
from farm.config import RELEASE_URL

logger = logging.getLogger("farm.release_info")


class FarmRelease:
    def __init__(self, release_uri=RELEASE_URL, access_token=None):
        self.farm_releases = None
        self.release_uri = release_uri
        self.access_token = access_token
        self.update_farm_releases()

    def update_farm_releases(self):
        try:
            self.farm_releases = self.farm_releases_dict(self.release_uri)
        except Exception as err:
            logger.error("Could not update release dictionary: {}".format(err))

    def farm_releases_dict(self, url):
        """
        Receive the content of ``url``, parse it as JSON and return the object.

        :return: dictionary of json data
        :rtype: dict

        :param url: website address
        :type url: str
        """
        try:
            if self.access_token:
                request = Request(url)
                request.add_header('Authorization', 'token {}'.format(self.access_token))
                response = urlopen(request)
            else:
                response = urlopen(url)
            data = response.read().decode("utf-8")
            return json.loads(data)
        except Exception as err:
            logger.error("Error: {}".format(err))
            return {}

    def github_releases(self, farm_releases, major_version):
        """ Return the tarball URL for the latest Farm release version """
        all_versions = []
        for each_release in farm_releases:
            if re.match('v{maj}.*(\d\.\d)'.format(maj=major_version),
                        each_release['name']):
                all_versions.append(each_release['name'][1:])
        return self.sort_reverse_list(all_versions)

    def github_latest_release(self, farm_releases):
        """ Return the latest Farm release version """
        all_versions = []
        for each_release in farm_releases:
            if re.match('v.*(\d\.\d\.\d)', each_release['name']):
                all_versions.append(each_release['name'][1:])
        try:
            return self.sort_reverse_list(all_versions)[0]
        except IndexError:
            return None

    def github_upgrade_exists(self):
        errors = []
        upgrade_exists = False
        releases = []
        current_latest_release = '0.0.0'
        try:
            current_latest_release = self.github_latest_release(self.farm_releases)
            current_maj_version = int(FARM_VERSION.split('.')[0])
            releases = self.github_releases(self.farm_releases, current_maj_version)

            if releases:
                if (parse_version(releases[0]) > parse_version(FARM_VERSION) or
                        parse_version(current_latest_release[0]) > parse_version(FARM_VERSION)):
                    upgrade_exists = True
        except Exception:
            logger.exception("github_upgrade_exists()")
            errors.append(
                "Could not determine local farm version or "
                "online release versions. Upgrade checks can "
                "be disabled in the Farm configuration.")
        return upgrade_exists, releases, self.farm_releases, current_latest_release, errors

    def is_latest_installed(self, major_number):
        """
        Check if the latest Farm release version is installed.
        Return True if yes, False if no.
        """
        latest_version = self.return_maj_version_url(True, major_number)
        if latest_version == FARM_VERSION:
            return True
        return False

    @staticmethod
    def sort_reverse_list(versions_unsorted):
        """
        Sort and reverse a list of strings representing Farm release version
        numbers in the format "x.x.x"

        :return: list of sorted version strings
        :rtype: list

        :param versions_unsorted: list of unsorted version strings
        :type versions_unsorted: list
        """
        versions_sorted = []
        for each_ver in versions_unsorted:
            versions_sorted.append(each_ver)
        versions_sorted.sort(key=lambda s: list(map(int, s.split('.'))))
        versions_sorted.reverse()
        return versions_sorted

    def return_latest_version_url(self, version_only):
        """ Return the tarball URL for the latest Farm release version """
        all_versions = []
        for each_release in self.farm_releases:
            if re.match('v.*(\d\.\d\.\d)', each_release['name']):
                all_versions.append(each_release['name'][1:])

        for each_release in self.farm_releases:
            if (re.match('v.*(\d\.\d\.\d)', each_release['name']) and
                    each_release['name'][1:] == self.sort_reverse_list(all_versions)[0]):
                if version_only:
                    return each_release['name'][1:]
                else:
                    return each_release['tarball_url']

    def return_maj_version_url(self, version_only, major_version):
        """
        Return the tarball URL for the Farm release version with the
        specified major number
        """
        maj_versions = []
        for each_release in self.farm_releases:
            if re.match('v{maj}.*(\d\.\d)'.format(maj=major_version),
                        each_release['name']):
                maj_versions.append(each_release['name'][1:])

        for each_release in self.farm_releases:
            if (re.match('v{maj}.*(\d\.\d)'.format(maj=major_version), each_release['name']) and
                    each_release['name'][1:] == self.sort_reverse_list(maj_versions)[0]):
                if version_only:
                    return each_release['name'][1:]
                else:
                    return each_release['tarball_url']

    def version_information(self, version_only, major_version):
        """
        Print all Farm releases, and specific info about
        latest and major releases
        """
        print("List of all Farm Releases:")

        for each_release in self.farm_releases:
            print("{ver} ".format(ver=each_release['name']))

        print(self.return_latest_version_url(version_only))
        print(self.return_maj_version_url(version_only, major_version))


def parseargs(p):
    p.add_argument('-c', '--currentversion', action='store_true',
                   help='Return the currently-installed version.')
    p.add_argument('-i', '--islatest', action='store_true',
                   help='Return True if the currently-installed '
                        'version is the latest.')
    p.add_argument('-l', '--latest', action='store_true',
                   help='Return the latest version URL.')
    p.add_argument('-m', '--majornumber', type=int,
                   help='Return the latest version URL with major '
                        'version number x in x.y.z.')
    p.add_argument('-v', '--version', action='store_true',
                   help='Return the latest version number.')
    return p.parse_args()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Returns information about Farm releases.')
    args = parseargs(parser)

    farm_release = FarmRelease()

    if args.islatest:
        print(farm_release.is_latest_installed(args.majornumber))
    elif args.currentversion:
        print(FARM_VERSION)
    elif args.latest or args.majornumber:
        if args.latest and args.majornumber:
            print("Error: Can only use -l or -m, not both.")
            parser.print_help()
        else:
            if args.latest:
                print(farm_release.return_latest_version_url(args.version))
            elif args.majornumber:
                print(farm_release.return_maj_version_url(args.version, args.majornumber))
    else:
        parser.print_help()
