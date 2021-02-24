import json
import re
from ipaddress import ip_network, collapse_addresses
from typing import List, Tuple

import requests


# TODO: bug with saving\loading cache (key error!)
# TODO: how to save custom added routes (routes not from this app) in system routing table?


def serialize_networks(networks: List[ip_network]) -> List[str]:
    return [str(ip_n) for ip_n in networks]


def deserialize_networks(networks: List[str]) -> List[ip_network]:
    return [ip_network(ip_n) for ip_n in networks]


class Source:
    URL: str = None
    CACHE_FILE = 'cached_sources.json'

    def __init__(self):
        self.cache = None
        self.last_etag = None
        self._read_cache()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def _parse(self, content: str) -> List[str]:
        raise NotImplemented

    def _read_cache(self):
        try:
            with open(self.CACHE_FILE, 'r') as f:
                self.cache = json.load(f)
            self.last_etag = self.cache[self.name]['ETag']
        except FileNotFoundError:
            self.cache = {self.name: {'ETag': self.last_etag,
                                      'Networks': []}}

    def _save_cache(self, etag: str, networks: List[str]):
        self.last_etag = etag
        self.cache[self.name] = {'ETag': self.last_etag,
                                 'Networks': networks}
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def get(self) -> Tuple[str, List[str]]:
        if not self.URL:
            raise NotImplemented

        networks = None
        new_etag = requests.head(self.URL).headers.get('ETAG', None)
        if not new_etag or new_etag != self.last_etag:
            new_etag = None if not new_etag else new_etag  # Set to None if value is not valid

            print('ETag is new or None. Download networks from source.')
            try:
                content = requests.get(self.URL).text
                networks = self._parse(content)
            except Exception as error:
                print(f'Error "{error}" during getting new networks. Return from cache.')
            else:
                self._save_cache(new_etag, networks)
                print('ETag and Networks are saved to cache.')
        else:
            print('ETag is not identified or the same.')

        if networks is None:
            print('Return from cache.')
            networks = self.cache[self.name]['Networks']

        return self.last_etag, networks


class ZaboronaHelpBase(Source):
    REGEXP = r'^\s*push\s+[\"\']route\s+(?P<IP>[\d.]+)(\s+(?P<MASK>[\d.]+))?\s*[\"\']'

    def _parse(self, content: str) -> List[str]:
        networks = []
        for line in content.split('\n'):
            matched = re.match(self.REGEXP, line)
            if matched:
                ip = matched.group('IP')
                mask = matched.group('MASK')
                if mask is None:
                    mask = '255.255.255.255'

                networks.append(f'{ip}/{mask}')

        return networks


class ZaboronaHelp1(ZaboronaHelpBase):
    URL = 'https://raw.githubusercontent.com/zhovner/zaborona_help/master/config/openvpn/ccd/DEFAULT'


class ZaboronaHelp2(ZaboronaHelpBase):
    URL = 'https://raw.githubusercontent.com/zhovner/zaborona_help/master/config/openvpn/ccd3-4_max_routes/DEFAULT'


class UABlackList(Source):
    URL = 'https://uablacklist.net/subnets.json'

    def _parse(self, content: str) -> List[str]:
        return json.loads(content)


class NetworksHandler:
    def __init__(self, sources: List[Source]):
        self.sources = sources
        self.source_etags = None
        self.networks = None

    def get_networks(self):
        self.networks = []
        for src in self.sources:
            # TODO: deserealize "old" cache from source here to get difference with new cache (get only new networks and networks to delete)
            etag, networks = src.get()  # TODO: etag is not used
            print(f'Networks from source "{src.name}" received. Got: {len(networks)} items.')
            self.networks.extend(deserialize_networks(networks))

        self.networks = list(collapse_addresses(self.networks))  # remove duplicates and optimization
        print(f'Total networks after optimization: {len(self.networks)} items.')


def main():
    sources = [ZaboronaHelp1(), ZaboronaHelp2(), UABlackList()]
    handler = NetworksHandler(sources)
    handler.get_networks()


if __name__ == '__main__':
    main()
