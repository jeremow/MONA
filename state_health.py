import cx_Oracle
from config import *
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class HatOracleClient:
    """
    The HatOracleClient object connect to the Oracle Client for the health states (also named HAT in mongolian).
    It initializes with the cx_Oracle library.
    It took out of the config.py file the CLIENT_ORACLE, HOST_ORACLE and PORT_ORACLE. Please verify the configuration
    before using it.
    """
    def __init__(self):
        cx_Oracle.init_oracle_client(CLIENT_ORACLE)
        self.dsn_tns = cx_Oracle.makedsn(HOST_ORACLE, PORT_ORACLE, service_name='xe')
        self.conn = cx_Oracle.connect(user=r'hat', password='hat', dsn=self.dsn_tns)
        self.cursor = self.conn.cursor()
        self.problem = []

    def write_state_health(self):
        """
        Pick the information needed in the Oracle Database and write it in the file log/server/states.xml.
        The XML file will be read by main app MONA-LISA to create the table of HAT/Health States.

        There are 5 basics parameters at first, but inside of this method, you'll find how to add more for your needs.
        :return: Nothing
        """
        try:
            stations = []
            states_data = f"<server ip='{HOST_ORACLE}' port='{PORT_ORACLE}'>"

            self.cursor.execute('SELECT STA, MAX(DATE1) FROM ALARMLOG GROUP BY STA')
            for row in self.cursor:
                stations.append([row[0], row[1]])

            for sta, timestamp in stations:
                states_data += f"<station name='{sta}'>"
                self.cursor.execute('SELECT * FROM ALARMLOG WHERE STA=:sta AND DATE1=:timestamp',
                                    sta=sta, timestamp=timestamp)
                row = self.cursor

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

                humidity = row[2]
                temp = row[3]
                alarm_loop = row[16]
                alarm_door = row[17]
                battery_voltage = row[29]

                self.verify_states(humidity=humidity,
                                   temp=temp,
                                   alarm_loop=alarm_loop,
                                   alarm_door=alarm_door,
                                   battery_voltage=battery_voltage)

                dt = f"D{timestamp.year}{timestamp.month}{timestamp.day}" \
                     f"T{timestamp.hour}{timestamp.minute}{timestamp.second}"
                states_data += f"""
                <state name='Humidity' datetime='{dt}' value='{humidity}%' problem='{self.problem[0]}'/> 
                <state name='Temperature' datetime='{dt}' value='{temp}°C' problem='{self.problem[1]}'/> 
                <state name='Solar Panel' datetime='{dt}' value='{alarm_loop}' problem='{self.problem[2]}'/> 
                <state name='Intrusion' datetime='{dt}' value='{alarm_door}' problem='{self.problem[3]}'/> 
                <state name='Battery Voltage' datetime='{dt}' value='{battery_voltage}V' problem='{self.problem[4]}'/> 
                """

                states_data += f"</station>"

            states_data += f"</server>"

            soup = BeautifulSoup(states_data, 'lxml-xml')

            with open('log/server/states.xml', 'w') as fp:
                fp.write(soup.prettify())

        except cx_Oracle.DatabaseError:
            print('Request is false')
        except FileNotFoundError:
            print('No states file found')

    def verify_states(self, **parameters):

        humidity = parameters.pop('humidity', 'None')
        temp = parameters.pop('temp', 'None')
        alarm_loop = parameters.pop('alarm_loop', 'None')
        alarm_door = parameters.pop('alarm_door', 'None')
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

        if alarm_loop is None:
            self.problem.append(-1)
        elif alarm_loop < 0 or alarm_loop > 0.9:
            self.problem.append(2)
        else:
            self.problem.append(0)

        if alarm_door is None:
            self.problem.append(-1)
        elif alarm_door < 0 or alarm_door > 0.9:
            self.problem.append(2)
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
        self.conn.close()
