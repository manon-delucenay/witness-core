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

import pandas as pd
from os.path import join, dirname
from climateeconomics.core.core_resources.resource_model.resource_disc import ResourceDiscipline
from climateeconomics.core.core_resources.models.copper_resource.copper_resource_model import CopperResourceModel
import numpy as np
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries,\
    TwoAxesInstanciatedChart


class CopperResourceDiscipline(ResourceDiscipline):
    ''' Discipline intended to get copper parameters
    '''

    # ontology information
    _ontology_data = {
        'label': 'Copper Resource Model',
        'type': 'Research',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fa-solid fa-reel',
        'version': '',
    }
    default_year_start = 2020
    default_year_end = 2100
    default_production_start = 1974
    default_years = np.arange(default_year_start, default_year_end + 1, 1)
    default_stock_start = 780.0
    default_recycled_rate = 0.5
    default_lifespan = 30
    default_sectorisation_dict = {'power_generation': 9.86175,
                                  'power_distribution_and_transmission': 35.13825,
                                  'construction': 20.0,
                                  'appliance_and_electronics': 12.5,
                                  'transports': 12.5,
                                  'other': 10.0}
    resource_name = CopperResourceModel.resource_name

    prod_unit = 'Mt'
    stock_unit = 'Mt'
    price_unit = '$/Mt'

    #Get default data for resource
    default_resource_data=pd.read_csv(join(dirname(__file__), f'../resources_data/{resource_name}_data.csv'))
    default_resource_production_data = pd.read_csv(join(dirname(__file__), f'../resources_data/{resource_name}_production_data.csv'))
    default_resource_price_data = pd.read_csv(join(dirname(__file__), f'../resources_data/{resource_name}_price_data.csv'))
    default_resource_consumed_data = pd.read_csv(join(dirname(__file__), f'../resources_data/{resource_name}_consumed_data.csv'))


    DESC_IN = {'resource_data': {'type': 'dataframe', 'unit': '[-]', 'default': default_resource_data,
                                 'user_level': 2, 'namespace': 'ns_copper_resource'},
               'resource_production_data': {'type': 'dataframe', 'unit': '[Mt]', 'optional': True,
                                            'default': default_resource_production_data, 'user_level': 2, 'namespace': 'ns_copper_resource'},
               'resource_price_data': {'type': 'dataframe', 'unit': '[$/Mt]', 'default': default_resource_price_data, 'user_level': 2,
                                       'dataframe_descriptor': {'resource_type': ('string', None, False),
                                                                'price': ('float', None, False),
                                                                'unit': ('string', None, False)},
                                       'namespace': 'ns_copper_resource'},
               'resource_consumed_data': {'type': 'dataframe', 'unit': '[Mt]', 'optional': True,
                                            'default': default_resource_consumed_data, 'user_level': 2, 'namespace': 'ns_copper_resource'},
               'production_start': {'type': 'float', 'default': default_production_start, 'unit': '[-]',
                                    'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_copper_resource'},
               'stock_start': {'type': 'float', 'default': default_stock_start, 'user_level': 2, 'unit': '[Mt]', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_copper_resource'},
               'recycled_rate': {'type': 'float', 'default': default_recycled_rate, 'user_level': 2, 'unit': '[-]', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_copper_resource'},
               'lifespan': {'type': 'int', 'default': default_lifespan, 'user_level': 2, 'unit': '[-]', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_copper_resource'},
               'sectorisation': {'type': 'dict', 'unit': '[-]', 'default': default_sectorisation_dict,'visibility': SoSDiscipline.SHARED_VISIBILITY,
                                 'user_level': 2, 'namespace': 'ns_copper_resource'}
               }

    DESC_IN.update(ResourceDiscipline.DESC_IN)

    DESC_OUT = {
        'resource_stock': {
            'type': 'dataframe', 'unit': 'Mt'},
        'resource_price': {
            'type': 'dataframe', 'unit': '$/t'},
        'use_stock': {
            'type': 'dataframe', 'unit': 'Mt'},
        'predictable_production': {
            'type': 'dataframe', 'unit': 'Mt'},
        'recycled_production' : {
            'type': 'dataframe', 'unit': 'Mt'}
    }

    DESC_OUT.update(ResourceDiscipline.DESC_OUT)

    def init_execution(self):
        inputs_dict = self.get_sosdisc_inputs()
        self.resource_model = CopperResourceModel(self.resource_name)
        self.resource_model.configure_parameters(inputs_dict)

        
        
