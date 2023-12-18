'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/22-2023/11/02 Copyright 2023 Capgemini

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
from sostrades_core.execution_engine.sos_wrapp import SoSWrapp
from sostrades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, \
    TwoAxesInstanciatedChart
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sostrades_core.execution_engine.data_connector.mock_connector import MockConnector
from sostrades_core.execution_engine.data_connector.data_connector_factory import ConnectorFactory


class Disc1(SoSWrapp):
    # ontology information
    _ontology_data = {
        'label': 'Disc1_data_connector',
        'type': 'Research',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fas fa-plane fa-fw',
        'version': '',
    }
    _maturity = 'Fake'

    data_connection_dict = {'connector_type': MockConnector.NAME,
                            'hostname': 'test_hostname',
                            'connector_request': None}

    dremio_path = '"test_request"'

    DESC_IN = {
        'x': {'type': 'float', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_ac'},
        'a': {'type': 'float'},
        'b': {'type': 'float'}
    }
    DESC_OUT = {
        'indicator': {'type': 'float'},
        'y': {'type': 'float', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_ac',
              SoSWrapp.CONNECTOR_DATA: data_connection_dict}
    }

    # get a connector_data with all information
    connector_data = ConnectorFactory.set_connector_request(
        DESC_OUT['y'][SoSWrapp.CONNECTOR_DATA], dremio_path)
    # update the meta_data with the new connection information
    # { var_name : {meta_dat_to_update : meta_data_value}}
    #     proxy.update_meta_data_out(
    #         {'y': {self.CONNECTOR_DATA: connector_data}})
    DESC_OUT['y'][SoSWrapp.CONNECTOR_DATA] = connector_data

    def run(self):
        x = self.get_sosdisc_inputs('x')
        a = self.get_sosdisc_inputs('a')
        b = self.get_sosdisc_inputs('b')
        # dict_values = {'indicator': a * b, 'y': a * x + b}
        dict_values = {'indicator': a * b}
        self.store_sos_outputs_values(dict_values)
