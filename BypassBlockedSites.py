import json
import os
import re
from ipaddress import ip_network, collapse_addresses
from typing import List, Tuple

import requests


# TODO: !!! implement Source as normal instance (not classmethods)
# TODO: !!! implement cache and etag checking, processing

def serialize_networks(networks: List[ip_network]) -> List[str]:
    return [str(ip_n) for ip_n in networks]


def deserialize_networks(networks: List[str]) -> List[ip_network]:
    return [ip_network(ip_n) for ip_n in networks]


class Source:
    URL: str = None
    CACHE_FILE = 'cached_sources.json'

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def _parse(cls, content: str) -> List[ip_network]:
        raise NotImplemented

    @classmethod
    def _get_cache_file(cls):
        if not os.path.exists(cls.CACHE_FILE):
            with open(cls.CACHE_FILE, 'w') as f:
                json.dump(dict(), f)  # create empty cache file if not exists

        with open(cls.CACHE_FILE, 'r') as f:
            return json.load(f)

    @classmethod
    def _save_cache(cls, etag, networks):
        networks = serialize_networks(networks)

        cache = cls._get_cache_file()
        cache[cls.name()] = {etag: networks}

        with open(cls.CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)

    # @classmethod
    # def _check_cache(cls):
    #     cache = cls._get_cache_file()

    @classmethod
    def get(cls) -> List[ip_network]:
        if not cls.URL:
            raise NotImplemented

        etag = requests.head(cls.URL).headers.get('ETAG', None)
        if etag:
            last_etag = list(cls._get_cache_file()[cls.name()].keys())[0]

            if etag == last_etag:
                print('ETag is the same. Content was not changed.')
                # TODO: return from cache?
                return deserialize_networks(cls._get_cache_file()[cls.name()][last_etag])
                # TODO: refactor

        networks = cls._parse(requests.get(cls.URL).text)
        cls._save_cache(etag, networks)

        return networks


class ZaboronaHelpBase(Source):
    REGEXP = r'^\s*push\s+[\"\']route\s+(?P<IP>[\d.]+)(\s+(?P<MASK>[\d.]+))?\s*[\"\']'

    @classmethod
    def _parse(cls, content: str) -> List[ip_network]:
        networks = []
        for line in content.split('\n'):
            matched = re.match(cls.REGEXP, line)
            if matched:
                ip = matched.group('IP')
                mask = matched.group('MASK')
                if mask is None:
                    mask = '255.255.255.255'
                networks.append(ip_network(f'{ip}/{mask}'))

        return networks


class ZaboronaHelp1(ZaboronaHelpBase):
    URL = 'https://raw.githubusercontent.com/zhovner/zaborona_help/master/config/openvpn/ccd/DEFAULT'


class ZaboronaHelp2(ZaboronaHelpBase):
    URL = 'https://raw.githubusercontent.com/zhovner/zaborona_help/master/config/openvpn/ccd3-4_max_routes/DEFAULT'


class UABlackList(Source):
    URL = 'https://uablacklist.net/subnets.json'

    @classmethod
    def _parse(cls, content: str) -> List[ip_network]:
        return deserialize_networks(json.loads(content))


class NetworksHandler:
    def __init__(self, sources: List[Source]):
        self.sources = sources
        self.source_etags = None
        self.networks = None

    def _load_sources_etags(sel):
        pass
        # TODO: continue

    def get_networks(self):
        self.networks = []
        for src in self.sources:
            try:
                networks = src.get()
                print(f'Networks from source "{src.name()}" received. Got: {len(networks)} items.')
                self.networks.extend(networks)
            except Exception as error:
                print(f'Error "{error}" while processing "{src.name()}" source.')

        self.networks = list(collapse_addresses(self.networks))  # remove duplicates and optimization
        print(f'Total networks after optimization: {len(self.networks)} items.')


def main():
    sources = [ZaboronaHelp1(), ZaboronaHelp2(), UABlackList()]
    handler = NetworksHandler(sources)
    handler.get_networks()


if __name__ == '__main__':
    main()
