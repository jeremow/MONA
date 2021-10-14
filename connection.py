# -*- coding: utf-8 -*-
# SIDEBAR TOP TO CONNECT TO SERVER, FOLDER, IMPORT A FILE

from obspy import UTCDateTime
from obspy.clients.seedlink import Client
from obspy.clients.seedlink.seedlinkexception import SeedLinkException

import xml.etree.ElementTree as ET


class ServerSeisComP3(Client):
    """
    ServerSeisComP3 class
    """
    def __init__(self, ip_address, port):
        self.connected = False
        self.ip_address = ip_address
        self.port = int(port)
        self.info = ''
        super(ServerSeisComP3, self).__init__(server=self.ip_address, port=self.port)

    # def connect_to_server(self, network, station, location, channel, starttime, endtime):
    #     try:
    #         _ = self.get_waveforms(network, station, location, channel, starttime, endtime)
    #
    #     except SeedLinkException:
    #         self.info = 'Config file is not matching with the SeedLink Server'


def create_client(server_info):
    try:
        info = server_info.split(':')
        ip_address = info[0]
        try:
            port = info[1]
        except IndexError:
            port = '18000'

    except IndexError:
        # Display the error message in case of an error in the writing of the IP
        info = 'Wrong syntax of IP'
        return None

    else:
        client = ServerSeisComP3(ip_address, port)
        return client, ip_address, port


def connection_client(client, ip_address, port, network_list, network_list_values):

    try:
        config_server = ET.parse('config/server/{}.xml'.format(ip_address + '.' + port))
        config_server_root = config_server.getroot()

        for network in config_server_root:
            network_name = network.attrib['name']

            for station in config_server_root.findall("./network[@name='{0}']/station".format(network_name)):
                station_name = station.attrib['name']

                for channel in config_server_root.findall("./network[@name='{0}']/"
                                                          "station[@name='{1}']/"
                                                          "channel".format(network_name, station_name)):
                    if channel.attrib['location'] == '':
                        channel_name = channel.attrib['name']
                    else:
                        location_name = channel.attrib['location']
                        channel_name = channel.attrib['name']

                        channel_name = location_name + '.' + channel_name

                    full_name = network_name + '.' + station_name + '.' + channel_name
                    network_list_values.append(full_name)
                    network_list.append({'label': full_name, 'value': full_name})
        return 1

    except FileNotFoundError:
        print('Config file of server missing.')
        return -1
    except IndexError:
        print('Verify the config file, no station found')
        return -2
