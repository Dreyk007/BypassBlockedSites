import json
import os
import re
from ipaddress import ip_network, collapse_addresses
from typing import List, Tuple

import requests


# TODO: how to save custom added routes (routes not from this app) in system routing table?


def serialize_networks(networks: List[ip_network]) -> List[str]:
    return [str(ip_n) for ip_n in networks]


def deserialize_networks(networks: List[str]) -> List[ip_network]:
    return [ip_network(ip_n) for ip_n in networks]


def dump_json(data: (list, dict), filepath: str):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_json(filepath: str) -> (list, dict):
    with open(filepath, 'r') as f:
        return json.load(f)


class Source:
    URL: str = None
    CACHE_DIR = 'cache'
    CACHE_FILE = 'cache_{name}.json'

    def __init__(self):
        self.last_etag = None
        self.cache = None
        self.cache_path = os.path.join(self.CACHE_DIR, self.CACHE_FILE.format(name=self.name))

        self._prepare()
        self._read_cache()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def _prepare(self):
        if not os.path.exists(self.cache_path):
            print(f'Cache path "{self.cache_path}" is not exists. Creating...')
            if not os.path.exists(self.CACHE_DIR):
                print(f'Cache dir "{self.CACHE_DIR}" is not exists. Creating...')
                os.mkdir(self.CACHE_DIR)

            empty_cache = {self.name: {'ETag': None,
                                       'Networks': []}
                           }
            dump_json(empty_cache, self.cache_path)

    def _parse(self, content: str) -> List[str]:
        raise NotImplemented

    def _read_cache(self):
        self.cache = load_json(self.cache_path)
        self.last_etag = self.cache[self.name]['ETag']

    def _save_cache(self, etag: str, networks: List[str]):
        self.last_etag = etag
        self.cache[self.name] = {'ETag': self.last_etag,
                                 'Networks': networks}
        dump_json(self.cache, self.cache_path)

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
