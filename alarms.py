import argparse
import os

import numpy
import numpy as np
from bs4 import BeautifulSoup as bs
from config import BUFFER_DIR, XML_INVENTORY

import pandas as pd
from scipy import interpolate

from obspy import Trace, UTCDateTime, read_inventory
from obspy.signal import PPSD
from obspy.signal.spectral_estimation import get_nhnm, get_nlnm

from utils import format_date_to_str


def create_alarm_from_HAT(type_connection='server'):
    """
    From the states file updated by HAT server, it creates alarms for the chosen SeedLink Server. This function is
    called in the update_states callback. It's made so because it can only change the alarms when the states of health
    are updated.
    Function writes into the server file alarms. The structure of this function is "complicated" because the database
    used in the IAG is not really unified. Like, they get data in a single database with twenty columns without the
    full name of the station like with a SeedLink process.
    :param type_connection:
    :return: nothing
    """

    if type_connection != 'server' and type_connection != 'folder':
        type_connection = 'server'

    # Read the XML file
    with open(f"log/{type_connection}/states.xml", "r", encoding='utf-8') as file:
        # Read each line in the file, readlines() returns a list of lines
        content_states = file.readlines()
        # Combine the lines in the list into a string
        content_states = "".join(content_states)
        bs_content_states = bs(content_states, 'lxml-xml')

    with open(f"log/{type_connection}/alarms.xml", 'r', encoding='utf-8') as alarms_file:
        content_alarms = alarms_file.readlines()
        content_alarms = "".join(content_alarms)
        bs_content_alarms = bs(content_alarms, 'lxml-xml')

    completed = bs_content_alarms.find('completed')

    if completed is None:
        completed = bs_content_alarms.new_tag('completed')

    stations = bs_content_states.find_all('station')
    alarms = f"<alarms><ongoing>"
    # WARNING ALARM
    for element in stations:
        station = element.get('name')
        for state_sta in element.find_all('state', {'problem': '1'}):
            state = state_sta.get('name')
            detail = state_sta.get('value')
            problem = '1'
            datetime = state_sta.get('datetime')
            _id = station + '.' + datetime + '.' + problem

            alarms += f"""
                <alarm id='{_id}' station='{station}' state='{state}' 
                detail='{detail}' datetime='{datetime}' problem='{problem}'/>
                """

        # CRITIC ALARM
        for state_sta in element.find_all('state', {'problem': '2'}):
            state = state_sta.get('name')
            detail = state_sta.get('value')
            problem = '2'
            datetime = state_sta.get('datetime')
            _id = station + '.' + datetime + '.' + problem

            alarms += f"""
                    <alarm id='{_id}' station='{station}' state='{state}' 
                    detail='{detail}' datetime='{datetime}' problem='{problem}'/>
                    """

    alarms += "</ongoing>"+str(completed)+"</alarms>"

    alarms = bs(alarms, 'lxml-xml')

    with open(f"log/{type_connection}/alarms.xml", 'w', encoding='utf-8') as fp:
        fp.write(alarms.prettify())


def create_alarm_from_data(type_connection='server'):
    """
    If data are visualized, it can creates alarms with the signal forms. You can add your own functions on data
    :return:
    """

    if type_connection != 'server' and type_connection != 'folder':
        type_connection = 'server'

    # CREATE ALARMS
    alarms = []
    for file in os.listdir(BUFFER_DIR):
        if file == 'streams.data':
            continue

        data = pd.read_feather(BUFFER_DIR+'/'+file)

        # here you implement probes

        datetime, detail, _id, problem, state, station = below_noise_model(file, data, XML_INVENTORY)


    # ADDING THE ALARMS TO THE FILE
    with open(f"log/{type_connection}/alarms.xml", 'r', encoding='utf-8') as alarms_file:
        content_alarms = alarms_file.readlines()
        content_alarms = "".join(content_alarms)
        bs_content_alarms = bs(content_alarms, 'lxml')


def below_noise_model(station, data, inv, save_plot=False):
    tr = df_to_trace(station, data)
    ppsd = PPSD(tr.stats, metadata=inv)
    ppsd.add(tr)

    fig = ppsd.plot(show=False)

    if save_plot:
        julday = format_date_to_str(tr.stats.starttime.julday, 3)
        fig.savefig(f"plot_data/psd/{station}/{tr.stats.starttime.year}.{julday}.png", dpi=300)

    nlnm_t, nlnm_db = get_nlnm()
    trace_t = ppsd.period_bin_centers.tolist()

    interp_func = interpolate.interp1d(nlnm_t, nlnm_db, bounds_error=False)
    interp_db = interp_func(trace_t)

    traces_db = ppsd.psd_values

    min_t = closest_index_of_list(trace_t, 2.5)
    max_t = closest_index_of_list(trace_t, 10)

    for t, trace_db in enumerate(traces_db):
        diff = np.substract(trace_db[min_t:max_t+1], interp_db[min_t, max_t+1])
        for i, element in enumerate(diff):
            if element < 0:
                time_processed = ppsd.times_processed[t]
                year = format_date_to_str(time_processed.year, 4)
                month = format_date_to_str(time_processed.month, 2)
                day = format_date_to_str(time_processed.day, 2)
                hour = format_date_to_str(time_processed.hour, 2)
                minute = format_date_to_str(time_processed.minute, 2)
                second = format_date_to_str(time_processed.second, 2)
                datetime = f'D{year}{month}{day}T{hour}{minute}{second}'
                _id = station + '.' + datetime + '.1'

                return datetime, f'{str(element)}dB', _id, 1, 'Below Low Noise Model', station

    return None, f'OK. BelowLowNoiseModel of {station}', None, 0, None, None


def df_to_trace(station, data):
    station = station.split('.')
    net, sta, loc, cha = station[0], station[1], station[2], station[3]

    data_x = data['Date'].values
    data_sta = data['Data_Sta'].values
    delta_t = data_x[1] - data_x[0]
    fs = round(numpy.timedelta64(1, 's') / delta_t, 1)
    starttime = UTCDateTime(str(data_x[0]))

    tr = Trace(data_sta)
    tr.stats.network = net
    tr.stats.station = sta
    tr.stats.location = loc
    tr.stats.channel = cha

    tr.stats.sampling_rate = fs
    tr.stats.starttime = starttime

    return tr


def closest_index_of_list(L, value):
    closest_element = abs(L[0] - value)
    closest_i = 0

    for i, element in enumerate(L):
        if abs(element - value) < closest_element:
            closest_element = abs(element - value)
            closest_i = i

    return closest_i





def get_arguments():
    """returns AttribDict with command line arguments"""
    parser = argparse.ArgumentParser(
        description='launch the alarms system',
        formatter_class=argparse.RawTextHelpFormatter)

    # Script functionalities
    parser.add_argument('-s', '--server', help='Path to SL server', required=True)
    parser.add_argument('-p', '--port', help='Port of the SL server')
    # parser.add_argument('-m', '--mseed', help='Path to mseed data folder', required=True)

    args = parser.parse_args()

    if args.port == None:
        args.port = '18000'

    print('Launching Alarms system of MONA-LISA...')
    print('Server: ', args.server)
    print('Port: ', args.port)
    print("--------------------------\n")

    return args


if __name__ == '__main__':
    args = get_arguments()

    create_alarm_from_data(args.server, args.port)
