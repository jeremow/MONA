# -*- coding: utf-8 -*-
# RETRIEVE_DATA.py
# Author: Jeremy
# Description: Client Seedlink adapté à MONA DASH

import argparse
import time
from utils import get_network_list
from threading import Thread

from obspy.clients.seedlink.client.seedlinkconnection import SeedLinkConnection
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.seedlink.seedlinkexception import SeedLinkException
from obspy.clients.seedlink.slpacket import SLPacket

from obspy import UTCDateTime

from config import *


class EasySLC(EasySeedLinkClient):
    def __init__(self, server_url, network_list, network_list_values,
                 data_retrieval=False, begin_time=None, end_time=None):
        self.network_list_values = network_list_values
        try:
            super(EasySLC, self).__init__(server_url, autoconnect=True)
            self.conn.timeout = 30
            self.data_retrieval = data_retrieval
            self.begin_time = begin_time
            self.end_time = end_time
            self.connected = 0

            self.connected = get_network_list('server', network_list, network_list_values,
                                              server_hostname=self.server_hostname, server_port=self.server_port)

            print(network_list_values)

            self.streams = []

        except SeedLinkException:
            pass

    def on_data(self, tr):
        print(tr)
        t_start = UTCDateTime()
        if tr is not None and t_start - tr.stats.starttime <= 300:

            tr.resample(sampling_rate=SAMPLING_RATE)
            tr.detrend(type='constant')

            if tr.stats.location == '':
                station = tr.stats.network + '.' + tr.stats.station + '..' + tr.stats.channel
            else:
                station = tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.location + '.' + tr.stats.channel

            x = pd.to_datetime(tr.times('timestamp'), unit='s')
            new_data_sta = pd.DataFrame({'Date': x, 'Data_Sta': tr.data})
            try:
                data_sta = pd.read_feather(BUFFER_DIR + '/' + station + '.data')
                if len(data_sta) <= 4500:
                    data_sta = pd.concat([data_sta, new_data_sta])
                else:
                    data_sta = pd.concat([data_sta[round(-len(data_sta) / 2):], new_data_sta])
            except FileNotFoundError:
                data_sta = new_data_sta
            data_sta = data_sta.reset_index(drop=True)
            data_sta.to_feather(BUFFER_DIR + '/' + station + '.data')

        elif t_start - tr.stats.starttime > 300:
            print(f'blockette is too old ({(t_start - tr.stats.starttime) / 60} min).')
        else:
            print("blockette contains no trace")

    def run(self):

        if self.data_retrieval is False:
            while True:
                try:
                    with open(BUFFER_DIR+'/streams.data', 'r') as file:
                        new_streams = file.read().splitlines()
                        if self.streams != new_streams:
                            self._EasySeedLinkClient__streaming_started = False
                            # streams = self.conn.streams.copy()
                            del self.conn
                            self.conn = SeedLinkConnection(timeout=30)
                            self.conn.set_sl_address('%s:%d' %
                                                     (self.server_hostname, self.server_port))
                            self.conn.multistation = True
                            for station in new_streams[1:]:
                                full_sta_name = station.split('.')
                                net = full_sta_name[0]
                                sta = full_sta_name[1]
                                cha = full_sta_name[2] + full_sta_name[3]
                                self.select_stream(net, sta, cha)

                            self.streams = new_streams.copy()

                except FileNotFoundError:
                    print('WAITING FOR STREAM FILE OF MONA-LISA')
                    time.sleep(5)
                    if self.data_retrieval:
                        self.on_terminate()
                        break
                else:
                    if self.data_retrieval:
                        self.on_terminate()
                        break

                    data = self.conn.collect()

                    if data == SLPacket.SLTERMINATE:
                        self.on_terminate()
                        continue
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
        elif self.begin_time is not None and self.end_time is not None:
            try:
                with open(BUFFER_DIR + '/streams.data', 'r') as file:
                    new_streams = file.read().splitlines()
                    self.on_terminate()
                    for station in new_streams[1:]:
                        full_sta_name = station.split('.')
                        net = full_sta_name[0]
                        sta = full_sta_name[1]
                        cha = full_sta_name[2] + full_sta_name[3]
                        self.select_stream(net, sta, cha)

            except FileNotFoundError:
                print('WAITING FOR STREAM FILE OF MONA-LISA')
                time.sleep(5)
            else:
                self.conn.set_begin_time(self.begin_time)
                self.conn.set_end_time(self.end_time)
                data = self.conn.collect()
                while data is not None:
                    if data == SLPacket.SLTERMINATE:
                        self.on_terminate()
                        continue

                    elif data == SLPacket.SLERROR:
                        self.on_seedlink_error()
                        continue
                    else:

                    # At this point the received data should be a SeedLink packet
                    # XXX In SLClient there is a check for data == None, but I think
                    #     there is no way that self.conn.collect() can ever return None
                        assert (isinstance(data, SLPacket))

                        packet_type = data.get_type()

                        # Ignore in-stream INFO packets (not supported)
                        if packet_type not in (SLPacket.TYPE_SLINF, SLPacket.TYPE_SLINFT):
                            # The packet should be a data packet
                            trace = data.get_trace()
                            # Pass the trace to the on_data callback
                            self.on_data(trace)
                        data = self.conn.collect()

    # ADAPT
    def on_terminate(self):
        self._EasySeedLinkClient__streaming_started = False
        streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.multistation = True
        self.conn.streams = streams.copy()
        # if self.data_retrieval is False:
        #     self.connect()

        # self.conn.begin_time = UTCDateTime()

    def on_seedlink_error(self):
        self._EasySeedLinkClient__streaming_started = False
        self.streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.multistation = True
        self.conn.streams = self.streams.copy()


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

    client = EasySLC(args.server + ':' + args.port, network_list, network_list_values, data_retrieval=True,
                     begin_time='2021,11,19,4,0,0', end_time='2021,11,19,4,0,30')

    print('Network list:', network_list_values)

    client.run()
