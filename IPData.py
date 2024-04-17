"""

A class to discover the network's WAN IP address and derive a gateway IP address.

Usage: 

    MyIP = IPData.IPData([noinit=True])
        Specify noinit to prevent an immediate call to the web service
        If uninitialized, a call to either 'get_' method below will call the web service

    MyWANIP = MyIP.get_wan_ip([format='list'])
        format='list' will return a list of octets. Any other value (or none) will return a string.
    MyGatewayIP = MyIP.get_gateway_ip([format='list'])
        format='list' will return a list of octets. Any other value (or none) will return a string.

"""

import requests

class IPData:
    initialized = False
    _ip = None
    wan_ip = None
    wan_ip_text = None
    gateway_ip = None
    gateway_ip_text = None


    def __init__(self, **opt):
        if opt.get('noinit'):
            pass
        else:
            self._ip_worker()
            self._parse_results()
            self.initialized = True


    def _ip_worker(self):
        try:
            print('_ip_worker invoked')
            self._ip = requests.get('https://api.my-ip.io/ip').text
        except Exception as e:
            self._ip = '0.0.0.0'


    def _parse_results(self):
        self.wan_ip_text = self._ip
        self.wan_ip = []
        self.wan_ip += [int(d) for d in self._ip.split('.')]
        self.gateway_ip = self.wan_ip[:3] + [1]
        self.gateway_ip_text = '.'.join(str(o) for o in self.gateway_ip)


    def get_wan_ip(self, **opt):
        if not self.initialized:
            self.__init__()
        if opt.get('format') == 'list':
            return self.wan_ip
        else:
            return self.wan_ip_text


    def get_gateway_ip(self, **opt):
        if not self.initialized:
            self.__init__()
        if opt.get('format') == 'list':
            return self.gateway_ip
        else:
            return self.gateway_ip_text


def main():
    MyIP = IPData()
    print('My WAN IP address:')
    print(MyIP.get_wan_ip())
    print(MyIP.get_wan_ip(format='list'))
    print(MyIP.get_wan_ip(format='raw'))
    print('My assumed gateway address:')
    print(MyIP.get_gateway_ip())
    print(MyIP.get_gateway_ip(format='list'))
    print(MyIP.get_gateway_ip(format='raw'))

if __name__ == '__main__':
    main()
