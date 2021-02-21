import re
from subprocess import check_output
from typing import List


class SystemRoutesHandlerBase:
    COMMAND_TO_GET_ROUTES = None
    COMMAND_TO_ADD_ROUTE = None
    COMMAND_TO_DELETE_ROUTE = None
    ENCODING = None

    def _parse(self, routes_raw: str) -> List[str]:
        raise NotImplemented

    def get(self) -> List[str]:
        routes_raw = check_output(self.COMMAND_TO_GET_ROUTES, encoding=self.ENCODING, shell=True)
        routes = self._parse(routes_raw)

        return routes

    def apply(self, routes_to_delete: List[str], routes_to_add: List[str]):
        raise NotImplemented


class SystemRoutesHandlerLinux(SystemRoutesHandlerBase):
    COMMAND_TO_GET_ROUTES = 'sudo ip route show'
    COMMAND_TO_ADD_ROUTE = 'sudo ip route add {route} via {vpn_gateway}'
    COMMAND_TO_DELETE_ROUTE = 'sudo ip route delete {route}'
    ENCODING = 'UTF-8'

    REGEXP = r'(?P<IP>\d+\.\d+\.\d+\.\d+)(?:/(?P<MASK>\d+))? via \d+\.\d+\.\d+\.\d+'
    CONFIG_FILE = '/etc/netplan/vpn_routes.yaml'

    def _get_main_iface_name(self):
        pass  # TODO: work with netplan?

    def _parse(self, routes_raw: str) -> List[str]:
        routes = []
        for line in routes_raw.split('\n'):
            matched = re.match(self.REGEXP, line)
            if matched:
                ip = matched.group('IP')
                mask = matched.group('MASK')
                if mask is None:
                    mask = '32'
                routes.append(f'{ip}/{mask}')

        return routes


if __name__ == '__main__':
    handler = SystemRoutesHandlerLinux()
    print(handler.get())
