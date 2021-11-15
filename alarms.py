from bs4 import BeautifulSoup as bs


def create_alarm_from_HAT(server, port):

    # Read the XML file
    with open("log/server/states.xml", "r", encoding='utf-8') as file:
        with open("log/server/"+server+'.'+port+"_alarms.xml", 'r', encoding='utf-8') as alarms_file:

            # Read each line in the file, readlines() returns a list of lines
            content_states = file.readlines()
            # Combine the lines in the list into a string
            content_states = "".join(content_states)
            bs_content_states = bs(content_states, 'lxml')

            content_alarms = alarms_file.readlines()
            content_alarms = "".join(content_alarms)
            bs_content_alarms = bs(content_alarms, 'lxml')

            completed = bs_content_alarms.find('completed')

            stations = bs_content_states.find_all('station')
            alarms = f"<server ip='{server}' port='{port}'><ongoing>"
            # WARNING ALARM
            for element in stations:
                station = element.attrs['name']
                for state_sta in element.find_all('state', {'problem': '1'}):
                    state = state_sta.get('name')
                    detail = state_sta.get('value')
                    problem = '1'
                    datetime = state_sta.get('datetime')
                    id = station + '.' + datetime + '.' + problem

                    alarms += f"""
                        <alarm id='{id}' station='{station}' state='{state}' 
                        detail='{detail}' datetime='{datetime}' problem='{problem}'/>
                        """

                # CRITIC ALARM
                for state_sta in element.find_all('state', {'problem': '2'}):
                    state = state_sta.get('name')
                    detail = state_sta.get('value')
                    problem = '2'
                    datetime = state_sta.get('datetime')
                    id = station + '.' + datetime + '.' + problem

                    alarms += f"""
                            <alarm id='{id}' station='{station}' state='{state}' 
                            detail='{detail}' datetime='{datetime}' problem='{problem}'/>
                            """

            alarms += "</ongoing>"

            alarms += str(completed)
            alarms = bs(alarms, 'xml')

    with open("log/server/"+server+'.'+port+"_alarms.xml", 'w', encoding='utf-8') as fp:
        fp.write(alarms.prettify())


if __name__ == '__main__':
    create_alarm_from_HAT('rtserver.ipgp.fr', '18000')