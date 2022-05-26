# -*- coding: utf-8 -*-
# mona_sl_client.py
# Author: Jeremy
# Description: SeedLink client for MONA, python dash version.

import time
# from threading import Thread

from obspy.clients.seedlink.client.seedlinkconnection import SeedLinkConnection
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.seedlink.seedlinkexception import SeedLinkException
from obspy.clients.seedlink.slpacket import SLPacket

from obspy import UTCDateTime

from config import *


class MonaSeedLinkClient(EasySeedLinkClient):
    """
    MonaSeedLinkClient is the class used in MONA to get data from a stream.data file of BUFFER_DIR in config.py.
    First version was threaded into app.py.
    New version is a standalone python script which is launched independently from the Dash app. It's waiting for the
    stream.data file created by MONA to retrieve data from the SeedLink Server. When the file stream.data changes, it
    will automatically update the SeedLink client with new information (changing the server, modifying the stations
    receiving list in realtime)

    Attributes
    ----------
    says_str : str
        a formatted string to print out what the animal says
    name : str
        the name of the animal
    sound : str
        the sound that the animal makes
    num_legs : int
        the number of legs the animal has (default 4)

    Methods
    -------
    on_data(tr)
        When a obspy trace is retrieved, it verifies the metadata, the expired time of it. If all good, it will save
        into a feather file in the BUFFER_DIR: NET.STA.LOC.CHA the duration QUEUE_DURATION of data into the file.
        If it's bigger, it will delete half of it to add the data (actually only 30 sec of data are interesting but we
        save around 180 sec. This can be changed in config.py)

    run()
        Here is the infinite loop of the SeedLink Client. Each time it gets through one step, it verifies that the
        streams.data file didn't change (server ip, port and stations). If there's a change, it reboot the connection
        and adapt it with the new parameters

    on_seedlink_error()
    on_terminate()
        They have the same way of working.They delete the connection and put it back on track. Especially useful for
        changing fast of retrieving stations. Maybe some performance increase have to be done here. This is my way.
    """
    def __init__(self, server_url, data_retrieval=False, begin_time=None, end_time=None):

        try:
            super(MonaSeedLinkClient, self).__init__(server_url, autoconnect=True)
            self.conn.timeout = 30
            self.data_retrieval = data_retrieval
            self.begin_time = begin_time
            self.end_time = end_time
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
                if len(data_sta) <= int(SAMPLING_RATE * QUEUE_DURATION):
                    data_sta = pd.concat([data_sta, new_data_sta])
                else:
                    data_sta = pd.concat([data_sta[round(-len(data_sta) / 2):], new_data_sta])
            except FileNotFoundError:
                data_sta = new_data_sta
            data_sta = data_sta.reset_index(drop=True)
            data_sta.to_feather(BUFFER_DIR + '/' + station + '.data')

        elif t_start - tr.stats.starttime > 300:
            print(f'blockette is too old ({(t_start - tr.stats.starttime) / 60} min).\n'
                  f'Problem could be incorrect computer datetime.')
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
                            new_streams_info = new_streams[0].split(':')
                            if len(new_streams_info) == 1:
                                self.server_hostname = new_streams_info[0]
                                self.server_port = 18000
                            else:
                                self.server_hostname = new_streams_info[0]
                                self.server_port = new_streams_info[1]
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
                    print('Waiting for streams.data file...')
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
                print('Waiting for streams.data file...')
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
        streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.multistation = True
        self.conn.streams = streams.copy()

# Deprecated thread class to launch MonaSeedlinkClient from app.py
# class SLThread(Thread):
#     def __init__(self, name, client):
#         Thread.__init__(self)
#         self.name = name
#         self.client = client
#
#     def run(self):
#         print('Starting Thread ', self.name)
#         print('Server: ', self.client.server_hostname)
#         print('Port:', self.client.server_port)
#         print("--------------------------\n")
#         print('Network list:', self.client.network_list_values)
#         self.client.run()
#
#     def close(self):
#         self.client.close()


if __name__ == '__main__':
    # Main algorithm to run the script. it's waiting for MONA to write the streams.data file. It's acting as a service.
    # Once the client run, it won't stop.
    while True:
        try:
            with open(BUFFER_DIR + '/streams.data', 'r') as file:
                streams = file.read().splitlines()
                streams_info = streams[0]
                client = MonaSeedLinkClient(streams_info)
            client.run()  # this is also an infinite loop, so if the client crashes, script will stay in the main
        except FileNotFoundError:
            print('Waiting for streams.data file...')
            time.sleep(5)
        except SeedLinkException:
            print('Verify the SeedLink connection information...')
            time.sleep(5)
