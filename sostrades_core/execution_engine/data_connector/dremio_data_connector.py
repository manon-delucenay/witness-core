'''
Copyright 2022 Airbus SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

from sostrades_core.execution_engine.data_connector.abstract_data_connector import AbstractDataConnector
import dremio_client


class DremioDataConnector(AbstractDataConnector):
    """
    Specific data connector for Dremio
    """

    data_connection_list = ['hostname',
                            'port', 'username', 'password']

    NAME = 'DREMIO'

    CONNECTOR_TYPE = 'connector_type'
    CONNECTOR_DATA = 'connector_data'
    CONNECTOR_REQUEST = 'connector_request'

    def __init__(self, data_connection_info=None):
        """
        Constructor for Dremio data connector

        :param data_connection_info: contains necessary data for connection
        :type data_connection_info: dict
        """

        self.hostname = None
        self.port = None
        self.username = None
        self.password = None

        super().__init__(data_connection_info=data_connection_info)

    def _extract_connection_info(self, data_connection_info):
        """
        Convert structure with data connection info given as parameter into member variable

        :param data_connection_info: contains necessary data for connection
        :type data_connection_info: dict
        """

        self.hostname = data_connection_info['hostname']
        self.port = data_connection_info['port']
        self.username = data_connection_info['username']
        self.password = data_connection_info['password']

    def load_data(self, connection_data):
        """
        Method to load a data from Dremio

        :param: connection_data_dict, contains the necessary information to connect to Dremio API : URL, port, usename, password
        :type: dict

        """

        self._extract_connection_info(connection_data)

        # connect to dremio_client.flight

        fl_client = dremio_client.flight.connect(
            hostname=self.hostname, port=self.port, username=self.username, password=self.password)

        # get the data from dremio

        dremio_path = connection_data[self.CONNECTOR_REQUEST]
        sql = '''
        SELECT * FROM  ''' + dremio_path
        data = dremio_client.flight.query(
            sql, fl_client)

        return data

    def write_data(self, connection_data):
        """
        Method to load a data from Dremio

        :param: connection_data_dict, contains the necessary information to connect to Dremio API : URL, port, usename, password
        :type: dict

        :param: dremio_path, identification of the data in dremio
        :type: string
        """

        raise Exception("method not implemented")

    def set_connector_request(self, connector_info, request):

        connector_info[DremioDataConnector.CONNECTOR_REQUEST] = request
        return connector_info
