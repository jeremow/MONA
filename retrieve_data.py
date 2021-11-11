# -*- coding: utf-8 -*-
# RETRIEVE_DATA.py
# Author: Jeremy
# Description: Client Seedlink adapté à MONA DASH

import argparse
import time
import xml.etree.ElementTree as ET
from threading import Thread

from obspy.clients.seedlink.client.seedlinkconnection import SeedLinkConnection
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.seedlink.seedlinkexception import SeedLinkException
from obspy.clients.seedlink.slpacket import SLPacket

from config import *


class EasySLC(EasySeedLinkClient):
    def __init__(self, server_url, network_list, network_list_values):
        self.network_list_values = network_list_values
        try:
            super(EasySLC, self).__init__(server_url)
            self.conn.timeout = 30
        except SeedLinkException:
            pass

        self.connected = 0

        try:
            config_server = ET.parse('config/server/{}.xml'.format(self.server_hostname + '.' + str(self.server_port)))
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
            self.connected = 1

        except FileNotFoundError:
            print('Config file of server missing.')
            self.connected = -1
        except IndexError:
            print('Verify the config file, no station found')
            self.connected = -2

        self.streams = []

    def on_data(self, tr):
        print(tr)
        if tr is not None:
            if tr.stats.location == '':
                station = tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.channel
            else:
                station = tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.location + '.' + tr.stats.channel

            x = pd.to_datetime(tr.times('timestamp'), unit='s')
            new_data_sta = pd.DataFrame({'Date': x, 'Data_Sta': tr.data})
            try:
                data_sta = pd.read_feather(BUFFER_DIR + '/' + station + '.data')
                if len(data_sta) <= 30000:
                    data_sta = pd.concat([data_sta, new_data_sta])
                else:
                    data_sta = pd.concat([data_sta[round(-len(data_sta) / 2):], new_data_sta])
            except FileNotFoundError:
                data_sta = new_data_sta
            data_sta = data_sta.reset_index(drop=True)
            data_sta.to_feather(BUFFER_DIR + '/' + station + '.data')
        else:
            print("blockette contains no trace")

    def run(self):
        streams = []
        while True:
            try:
                with open(BUFFER_DIR+'/streams.data', 'r') as file:
                    new_streams = file.read().splitlines()
                    if streams != new_streams:
                        self.on_terminate()
                        for station in new_streams[1:]:
                            full_sta_name = station.split('.')
                            if len(full_sta_name) == 3:
                                net = full_sta_name[0]
                                sta = full_sta_name[1]
                                cha = full_sta_name[2]
                            else:
                                net = full_sta_name[0]
                                sta = full_sta_name[1]
                                cha = full_sta_name[2] + full_sta_name[3]
                            self.select_stream(net, sta, cha)
                        streams = new_streams.copy()
            except FileNotFoundError:
                print('WAITING FOR STREAM FILE OF MONA-LISA')
                time.sleep(5)
            else:
                data = self.conn.collect()

                if data == SLPacket.SLTERMINATE:
                    self.on_terminate()
                    break
                elif data == SLPacket.SLERROR:
                    self.on_seedlink_error()
                    continue

                # At this point the received data should be a SeedLink packet
                # XXX In SLClient there is a check for data == None, but I think
                #     there is no way that self.conn.collect() can ever return None
                assert(isinstance(data, SLPacket))

                packet_type = data.get_type()

                # Ignore in-stream INFO packets (not supported)
                if packet_type not in (SLPacket.TYPE_SLINF, SLPacket.TYPE_SLINFT):
                    # The packet should be a data packet
                    trace = data.get_trace()
                    # Pass the trace to the on_data callback
                    self.on_data(trace)

    def on_terminate(self):
        self._EasySeedLinkClient__streaming_started = False
        self.close()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.connect()

        # self.conn.begin_time = UTCDateTime()

    def on_seedlink_error(self):
        self._EasySeedLinkClient__streaming_started = False
        self.close()
        self.streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.streams = self.streams.copy()
        self.run()


class SLThread(Thread):
    def __init__(self, name, client):
        Thread.__init__(self)
        self.name = name
        self.client = client

    def run(self):
        print('Starting Thread ', self.name)
        print('Server: ', self.client.server_hostname)
        print('Port:', self.client.server_port)
        print("--------------------------\n")
        print('Network list:', self.client.network_list_values)
        self.client.run()

    def close(self):
        self.client.close()


def get_arguments():
    """returns AttribDict with command line arguments"""
    parser = argparse.ArgumentParser(
        description='launch a seedlink server',
        formatter_class=argparse.RawTextHelpFormatter)

    # Script functionalities
    parser.add_argument('-s', '--server', help='Path to SL server', required=True)
    parser.add_argument('-p', '--port', help='Port of the SL server')
    # parser.add_argument('-m', '--mseed', help='Path to mseed data folder', required=True)

    args = parser.parse_args()

    if args.port == None:
        args.port = '18000'

    print('Server: ', args.server)
    print('Port: ', args.port)
    print("--------------------------\n")

    return args


if __name__ == '__main__':
    args = get_arguments()

    network_list = []
    network_list_values = []

    client = EasySLC(args.server + ':' + args.port, network_list, network_list_values)

    print('Network list:', network_list_values)

    client.run()
