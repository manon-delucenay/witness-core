'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/08-2023/11/02 Copyright 2023 Capgemini

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

import abc

class AbstractDataConnector(abc.ABC):
    """ 
    Abstract class to inherit in order to build specific data connector
    """

    data_connection_list = []
    CONNECTOR_TYPE = 'connector_type'
    CONNECTOR_MODE = 'connector_mode'

    CONNECTOR_MODE_READ = 'read'
    CONNECTOR_MODE_WRITE = 'write'

    def __init__(self, data_connection_info=None):
        """
        generic constructor for data connector

        :param data_connection_info: contains necessary data for connection
        :type data_connection_info: dict
        """

        if data_connection_info is not None:
            self._extract_connection_info(data_connection_info)

    @abc.abstractmethod
    def _extract_connection_info(self, data_connection_info):
        """
        Convert structure with data connection info given as parameter into member variable

        :param data_connection_info: contains necessary data for connection
        :type data_connection_info: dict
        """

    @abc.abstractmethod
    def load_data(self, connector_info):
        """
        Abstract method to overload in order to load a data from a specific API
        """

    @abc.abstractmethod
    def write_data(self, request):
        """
        Abstract method to overload in order to read a data from a specific API
        """

    @abc.abstractmethod
    def set_connector_request(self, connector_info, request):
        """
        Abstract method to overload in order set request into the connector data structure
        """

    def get_data_from_loaded_db(self, loaded_data, var_name):
        """
        get data from loaded data for given variable 
        :param loaded_data: data from which we should extract value 
        :type dict, dataframe
        :param var_name: name of variable name to get the value
        :type string
        """
        # if data is a dictionnary get data if variable in dictionnary, else return None
        if isinstance(loaded_data, dict):
            if var_name in loaded_data:
                return loaded_data[var_name]
            else:
                return None 
        else:
            return None


    def get_connector_mode(self, connector_info):
        """
        Get the read write connection mode from connector info
        """
        connector_mode = self.CONNECTOR_MODE_READ
        if self.CONNECTOR_MODE in connector_info.keys():
            connector_mode = connector_info[self.CONNECTOR_MODE]
        return connector_mode
