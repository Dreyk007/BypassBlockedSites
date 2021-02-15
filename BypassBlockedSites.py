import json
import re
from ipaddress import ip_network, collapse_addresses
from typing import List, Tuple

import requests


class Source:
    URL: str = None

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def _parse(cls, content: str) -> List[ip_network]:
        raise NotImplemented

    @classmethod
    def get(cls, last_etag: str = '') -> Tuple[List[ip_network], str]:
        if not cls.URL:
            raise NotImplemented

        etag = requests.head(cls.URL).headers.get('ETAG', '')
        if etag and etag == last_etag:
            return [], etag
        return cls._parse(requests.get(cls.URL).text), etag


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
        return [ip_network(ip_n) for ip_n in json.loads(content)]


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
                networks, src_etag = src.get()
                print(f'Networks from source "{src.name()}" received. Got: {len(networks)} items. ETag: {src_etag}.')
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
