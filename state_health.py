import cx_Oracle
from config import *
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class HatOracleClient:
    def __init__(self):
        cx_Oracle.init_oracle_client(CLIENT_ORACLE)
        self.dsn_tns = cx_Oracle.makedsn(HOST_ORACLE, PORT_ORACLE, service_name='xe')
        self.conn = cx_Oracle.connect(user=r'hat', password='hat', dsn=self.dsn_tns)
        self.cursor = self.conn.cursor()
        self.problem = []

    def write_state_health(self):
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
                humidity, temp, alarm_loop, alarm_door, battery_voltage = row[2], row[3], row[16], row[17], row[29]

                self.verify_states(humidity, temp, alarm_loop, alarm_door, battery_voltage)

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

    def verify_states(self, humidity, temp, alarm_loop, alarm_door, battery_voltage):
        self.problem = []
        if humidity is None:
            self.problem.append(-1)
        elif humidity < 5 or humidity > 99:
            self.problem.append(2)
        elif humidity < 10 or humidity > 90:
            self.problem.append(1)
        else:
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

    def close(self):
        self.conn.close()
