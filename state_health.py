import cx_Oracle
from config import *
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as bs
from utils import format_date_to_str, format_states_dt


class HatOracleClient:
    """
    The HatOracleClient object connect to the Oracle Client for the health states (also named HAT in mongolian).
    It initializes with the cx_Oracle library.
    It took out of the config.py file the CLIENT_ORACLE_XAT, HOST_ORACLE_XAT and PORT_ORACLE. Please verify the configuration
    before using it.
    """
    def __init__(self):
        try:
            cx_Oracle.init_oracle_client(CLIENT_ORACLE_XAT)
        except cx_Oracle.DatabaseError as e:
            print(e)
            print(f"Variable CLIENT_ORACLE_XAT for the Oracle Client software not/badly configured in config.py.\n"
                  f"Value: {CLIENT_ORACLE_XAT}.")
            exit(1)
        self.dsn_tns = cx_Oracle.makedsn(HOST_ORACLE_XAT, PORT_ORACLE_XAT, service_name=SERVICE_ORACLE_XAT)
        try:
            self.conn = cx_Oracle.connect(user=USER_ORACLE_XAT, password=PWD_ORACLE_XAT, dsn=self.dsn_tns)
            self.cursor = self.conn.cursor()
            self.stations = []
            self.cursor.execute(f'SELECT STATION_NAME FROM {TABLE_ORACLE_XAT} GROUP BY STATION_NAME')
            for row in self.cursor:
                self.stations.append(row[0])
        except cx_Oracle.ProgrammingError:
            print('Connection error for HatOracleClient')
        except cx_Oracle.DatabaseError:
            print('Connection error for HatOracleClient')

    def write_state_health(self):
        """
        Pick the information needed in the Oracle Database and write it in the file log/server/states_xat.xml.
        The XML file will be read by main app MONA-LISA to create the table of HAT/Health States.

        There are 5 basics parameters at first, but inside of this method, you'll find how to add more for your needs.
        :return: Nothing
        """
        try:
            states_data = f"<server ip='{HOST_ORACLE_XAT}' port='{PORT_ORACLE_XAT}'>"
            for sta in self.stations:
                states_data += f"<station name='{sta}'>"
                self.cursor.execute(f'SELECT * FROM {TABLE_ORACLE_XAT} WHERE '
                                    f'STATION_NAME=:sta AND IS_DATA=:data ORDER BY TIME DESC',
                                    sta=sta, data='Data')
                for row in self.cursor:

                    # HOW TO ADD A NEW PARAMETER FROM THE DATABASE OF HEALTH STATES
                    # 1: Search the row in your database and add a line below with the name of it
                    # 2: in the self.verify_states method, add the line in between the parenthesis "param=param".
                    #    Don't forget the comma at the end of the already written last parameter
                    # 3: Add a line in the variable states_data with the formatted name of your parameter "Your Param".
                    #    The name of the variable written by you with its unit {param}Unit and you add one to the number
                    #    inside of the self.problem[i+1] attribute. Format:
                    #    <state name='Your Param' datetime='{dt}' value='{param}Unit' problem='{self.problem[i+1]}'/>
                    #    Example:
                    #    <state name='Current' datetime='{dt}' value='{current}A' problem='{self.problem[5]}'/>
                    # 4: In the method verify_states, you add the line: param = parameters.pop('param', 'None')
                    # 5: You add the criteria afterwards like the model in the verify_states method.

                    timestamp = row[0]

                    vault0_temperature = row[2]
                    vault0_humidity = row[3]
                    vault1_temperature = row[4]
                    vault1_humidity = row[5]
                    seismometer_temperature = row[6]
                    outside_temperature = row[7]
                    vpn_voltage = row[8]
                    vpn_current = row[9]
                    telemeter_voltage = row[10]
                    telemeter_current = row[11]
                    digitizer_voltage = row[12]
                    digitizer_current = row[13]
                    computer_voltage = row[14]
                    computer_current = row[15]
                    device_voltage = row[16]
                    device_current = row[17]
                    sensor1_value = row[18]


                    # self.verify_states(humidity=humidity,
                    #                    temp=temp,
                    #                    # alarm_loop=alarm_loop,
                    #                    # alarm_door=alarm_door,
                    #                    battery_voltage=battery_voltage)

                    dt = format_states_dt(timestamp)

                    states_data += f"""
                    <state name='Temperature Station vault' datetime='{dt}' value='{vault0_temperature}°C' problem='0' /> 
                    <state name='Humidity Station vault' datetime='{dt}' value='{vault0_humidity}%' problem='0'/> 
                    <state name='Temperature Second vault' datetime='{dt}' value='{vault1_temperature}°C' problem='0'/> 
                    <state name='Humidity Second vault' datetime='{dt}' value='{vault1_humidity}%' problem='0'/> 
                    <state name='Temperature Seismometer' datetime='{dt}' value='{seismometer_temperature}°C' problem='0'/> 
                    <state name='Temperature Outside' datetime='{dt}' value='{outside_temperature}°C' problem='0'/> 
                    <state name='VPN Voltage' datetime='{dt}' value='{vpn_voltage}V' problem='0'/> 
                    <state name='VPN Current' datetime='{dt}' value='{vpn_current}A' problem='0'/> 
                    <state name='Telemeter Voltage' datetime='{dt}' value='{telemeter_voltage}V' problem='0'/> 
                    <state name='Telemeter Current' datetime='{dt}' value='{telemeter_current}A' problem='0'/> 
                    <state name='Digitizer Voltage' datetime='{dt}' value='{digitizer_voltage}V' problem='0'/> 
                    <state name='Digitizer Current' datetime='{dt}' value='{digitizer_current}A' problem='0'/> 
                    <state name='Computer Voltage' datetime='{dt}' value='{computer_voltage}V' problem='0'/> 
                    <state name='Computer Current' datetime='{dt}' value='{computer_current}A' problem='0'/> 
                    <state name='Device Voltage' datetime='{dt}' value='{device_voltage}V' problem='0'/> 
                    <state name='Device Current' datetime='{dt}' value='{device_current}A' problem='0'/>
                    <state name='Saxiul XAT' datetime='{dt}' value='{sensor1_value[0]}' problem='0'/>
                    <state name='Water XAT' datetime='{dt}' value='{sensor1_value[1]}' problem='0'/>
                    <state name='Door 1 XAT' datetime='{dt}' value='{sensor1_value[2]}' problem='0'/>
                    <state name='Door 2 XAT' datetime='{dt}' value='{sensor1_value[3]}' problem='0'/>
                    <state name='Loop XAT' datetime='{dt}' value='{sensor1_value[5]}' problem='0'/>
                    """

                    states_data += f"</station>"
                    break  # to leave the current cursor after getting the last value

                self.cursor.execute(f'SELECT * FROM {TABLE_ORACLE_XAT} WHERE '
                                    f'STATION_NAME=:sta AND IS_DATA=:data ORDER BY TIME DESC',
                                    sta=sta, data='Alarm')
                for row in self.cursor:
                    timestamp = row[0]
                    alarm = row[19]
                    dt = format_states_dt(timestamp)
                    self.analyze_alarm(sta, alarm, dt)
                    break  # to leave the current cursor after getting the last value

            states_data += f"</server>"

            soup = bs(states_data, 'lxml-xml')

            with open('log/server/states_xat.xml', 'w', encoding='utf-8') as fp:
                fp.write(soup.prettify())

        except cx_Oracle.DatabaseError:
            print('Request is false')
        except FileNotFoundError:
            print('No states file found')

    def analyze_alarm(self, station, alarm, dt):
        try:
            with open('log/server/alarms.xml', 'r', encoding='utf-8'):
                pass
        except FileNotFoundError:
            alarms_content = """
            <alarms>
                <ongoing></ongoing>
                <completed></completed>
            </alarms>
            """
            alarms = bs(alarms_content, 'lxml-xml')
            with open(f"log/server/alarms.xml", 'w', encoding='utf-8') as fp:
                fp.write(alarms.prettify())

        try:
            normal_state = XAT_NORMAL_STATE[station]
            with open(f"log/server/alarms.xml", 'r', encoding='utf-8') as alarms_file:
                content_alarms = alarms_file.readlines()
                content_alarms = "".join(content_alarms)
                bs_content_alarms = bs(content_alarms, 'lxml-xml')
                ongoing_alarms = bs_content_alarms.find('ongoing')
                for i, state in enumerate(alarm):
                    if state != normal_state[i]:
                        name = XAT_ALARM_NAME[i]
                        name = name.replace(' ', '_')
                        problem = '2'
                        _id = f"{station}.{name}.{problem}"
                        alarm_og = ongoing_alarms.find('alarm', {'id': _id})
                        if alarm_og is not None:
                            alarm_og['datetime'] = dt
                        else:
                            new_alarm = bs_content_alarms.new_tag('alarm')
                            new_alarm['datetime'] = dt
                            new_alarm['detail'] = ''
                            new_alarm['id'] = _id
                            new_alarm['problem'] = problem
                            new_alarm['state'] = name
                            new_alarm['station'] = station
                            bs_content_alarms.alarms.ongoing.append(new_alarm)
            with open("log/server/alarms.xml", 'w', encoding='utf-8') as fp:
                fp.write(bs_content_alarms.prettify())
        except KeyError:
            print(f"Normal state for XAT station {station} not in config.py.")
        except IndexError:
            print(f"Not enough XAT_ALARM_NAME in config.py to write alarm.")

    def verify_states(self, **parameters):

        humidity = parameters.pop('humidity', 'None')
        temp = parameters.pop('temp', 'None')
        # alarm_loop = parameters.pop('alarm_loop', 'None')
        # alarm_door = parameters.pop('alarm_door', 'None')
        battery_voltage = parameters.pop('battery_voltage', 'None')
        # add here your new parameters
        # current = parameters.pop('current', 'None') ...

        self.problem = []  # don't touch this line

        # Criteria for Humidity
        if humidity is None:  # If no data about it, we add -1 to the list problem (it's equal to N/A)
            self.problem.append(-1)
        elif humidity < 5 or humidity > 99:  # criteria for the critical problem, we add 2 to the list problem if happen
            self.problem.append(2)
        elif humidity < 10 or humidity > 90:  # criteria warning problem, we add 1 the the list problem it it happens
            self.problem.append(1)
        else:  # else normal situation, so we add 0 to the list problem
            self.problem.append(0)

        if temp is None:
            self.problem.append(-1)
        elif temp < -30 or temp > 60:
            self.problem.append(2)
        elif temp < -5 or temp > 40:
            self.problem.append(1)
        else:
            self.problem.append(0)

        if battery_voltage is None:
            self.problem.append(-1)
        elif battery_voltage < 11 or battery_voltage > 17:
            self.problem.append(2)
        elif battery_voltage < 12 or battery_voltage > 14.92:
            self.problem.append(1)
        else:
            self.problem.append(0)

        # Model for a new parameter called current (example)
        # if current is None:
        #     self.problem.append(-1)
        # elif current < 0 or current > 3:
        #     self.problem.append(2)
        # elif battery_voltage < 0 or battery_voltage > 2.5:
        #     self.problem.append(1)
        # else:
        #     self.problem.append(0)

    def close(self):
        self.cursor.close()
        self.conn.close()


class SOHOracleClient:
    """
    The SOHOracleClient object connect to the Oracle Client for the health states (also named SOH).
    It initializes with the cx_Oracle library.
    It took out of the config.py file the CLIENT_ORACLE_SOH, HOST_ORACLE_SOH and PORT_ORACLE_SOH. Please verify the
    configuration before using it.
    """
    def __init__(self):
        try:
            cx_Oracle.init_oracle_client(CLIENT_ORACLE_SOH)
        except cx_Oracle.DatabaseError as e:
            print(e)
            print(f"Variable CLIENT_ORACLE_SOH for the Oracle Client software not/badly configured in config.py.\n"
                  f"Value: {CLIENT_ORACLE_SOH}.")
            exit(1)
        self.dsn_tns = cx_Oracle.makedsn(HOST_ORACLE_SOH, PORT_ORACLE_SOH, service_name=SERVICE_ORACLE_SOH)
        try:
            self.conn = cx_Oracle.connect(user=USER_ORACLE_SOH, password=PWD_ORACLE_SOH, dsn=self.dsn_tns)
            self.cursor = self.conn.cursor()

            self.stations = []
            for TABLE in TABLE_ORACLE_SOH:
                self.cursor.execute(f'SELECT STATION FROM {TABLE} GROUP BY STATION')
                for row in self.cursor:
                    sta = row[0]
                    if sta not in self.stations:
                        self.stations.append(sta)
        except cx_Oracle.ProgrammingError:
            print('Connection error for SOHOracleClient')
        except cx_Oracle.DatabaseError:
            print('Connection error for SOHOracleClient')
        self.problem = []

    def write_state_health(self):
        """
        Pick the information needed in the Oracle Database and write it in the file log/server/states_soh.xml.
        The XML file will be read by main app MONA-LISA to create the table of HAT/SOH.

        There are 5 basics parameters at first, but inside of this method, you'll find how to add more for your needs.
        :return: Nothing
        """
        try:

            states_data = f"<server ip='{HOST_ORACLE_SOH}' port='{PORT_ORACLE_SOH}'>"

            for sta in self.stations:
                states_data += f"<station name='{sta}'>"

                self.cursor.execute(f'SELECT * FROM {TABLE_ORACLE_SOH[0]} WHERE STATION=:sta ORDER BY DATE1 DESC',
                                    sta=sta)
                for row in self.cursor:
                    timestamp = row[0]
                    used_disksize = row[1]
                    available_disksize = row[2]
                    total_disksize = row[3]

                    dt = format_states_dt(timestamp)

                    states_data += f"""
                    <state name='Used Disk size' datetime='{dt}' value='{used_disksize}' /> 
                    <state name='Available Disk size' datetime='{dt}' value='{available_disksize}' /> 
                    <state name='Total Disk size' datetime='{dt}' value='{total_disksize}' /> 
                    """
                    break  # to leave the current cursor after getting the last value

                self.cursor.execute(f'SELECT * FROM {TABLE_ORACLE_SOH[1]} WHERE STATION=:sta ORDER BY DATE1 DESC',
                                    sta=sta)
                for row in self.cursor:
                    timestamp = row[0]
                    e_massposition = row[1]
                    n_massposition = row[2]
                    z_massposition = row[3]

                    dt = format_states_dt(timestamp)

                    states_data += f"""
                    <state name='E Mass position' datetime='{dt}' value='{e_massposition}' /> 
                    <state name='N Mass position' datetime='{dt}' value='{n_massposition}' /> 
                    <state name='Z Mass position' datetime='{dt}' value='{z_massposition}' /> 
                    """
                    break  # to leave the current cursor after getting the last value

                self.cursor.execute(f'SELECT * FROM {TABLE_ORACLE_SOH[2]} WHERE STATION=:sta ORDER BY DATE1 DESC',
                                    sta=sta)
                for row in self.cursor:
                    timestamp = row[0]
                    battery_voltage = row[1]
                    temperature = row[2]

                    dt = format_states_dt(timestamp)

                    states_data += f"""
                    <state name='Battery voltage station' datetime='{dt}' value='{battery_voltage}' /> 
                    <state name='Temperature' datetime='{dt}' value='{temperature}' /> 
                    """
                    break

                states_data += f"</station>"
            states_data += f"</server>"

            soup = bs(states_data, 'lxml-xml')

            with open('log/server/states_soh.xml', 'w', encoding='utf-8') as fp:
                fp.write(soup.prettify())

        except cx_Oracle.DatabaseError:
            print('Request is false')
        except FileNotFoundError:
            print('No states file found')

    def verify_states(self, **parameters):
        pass

    def close(self):
        self.cursor.close()
        self.conn.close()
