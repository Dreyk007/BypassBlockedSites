import re
from subprocess import run, check_output
from typing import List

from config import Config


# TODO: so "routes" or "networks"?
# TODO: where to create instance of Config to provide it everywhere?
# TODO: need to save which ETag and routes are applied to the system. Also need to calc md5 for route sets (for comparing in client-server mode).


class SystemRoutesHandlerBase:
    COMMAND_TO_GET_ROUTES = None
    COMMAND_TO_ADD_ROUTE = None
    COMMAND_TO_DELETE_ROUTE = None
    ENCODING = None

    def _parse(self, routes_raw: str) -> List[str]:
        raise NotImplemented

    def get(self) -> List[str]:
        routes_raw = self.exe_cmd(self.COMMAND_TO_GET_ROUTES, output=True)
        routes = self._parse(routes_raw)

        return routes

    def apply(self, routes_to_delete: List[str], routes_to_add: List[str]):
        for route in routes_to_delete:
            self._del(route)

        for route in routes_to_add:
            self._add(route)

    def _add(self, route: str):
        raise NotImplemented

    def _del(self, route: str):
        raise NotImplemented

    def exe_cmd(self, cmd: str, output: bool = False):
        if not cmd:
            raise NotImplemented
        if output:
            return check_output(cmd, encoding=self.ENCODING, shell=True)
        run(cmd, check=True, shell=True)


class SystemRoutesHandlerLinux(SystemRoutesHandlerBase):
    COMMAND_TO_GET_ROUTES = 'ip route show'
    COMMAND_TO_ADD_ROUTE = 'ip route add {route} dev {ip_vpn_devname}'
    COMMAND_TO_DELETE_ROUTE = 'ip route delete {route} dev {ip_vpn_devname}'
    ENCODING = 'UTF-8'

    REGEXP = r'(?P<IP>\d+\.\d+\.\d+\.\d+)(?:/(?P<MASK>\d+))? dev {ip_vpn_devname}'.format(
        ip_vpn_devname=Config.IP_VPN_DEVNAME
    )

    def _parse(self, routes_raw: str) -> List[str]:
        networks = []
        for line in routes_raw.split('\n'):
            matched = re.match(self.REGEXP, line)
            if matched:
                ip = matched.group('IP')
                mask = matched.group('MASK')
                if mask is None:
                    mask = '32'
                networks.append(f'{ip}/{mask}')

        return networks

    def _add(self, route: str):
        cmd = self.COMMAND_TO_ADD_ROUTE.format(route=route, ip_vpn_devname=Config.IP_VPN_DEVNAME)
        self.exe_cmd(cmd)

    def _del(self, route: str):
        cmd = self.COMMAND_TO_DELETE_ROUTE.format(route=route, ip_vpn_devname=Config.IP_VPN_DEVNAME)
        self.exe_cmd(cmd)


if __name__ == '__main__':
    handler = SystemRoutesHandlerLinux()
    print(handler.get())
    handler.apply(routes_to_delete=[], routes_to_add=['8.8.8.8/32'])
    print(handler.get())
    handler.apply(routes_to_delete=['8.8.8.8/32'], routes_to_add=[])
    print(handler.get())
