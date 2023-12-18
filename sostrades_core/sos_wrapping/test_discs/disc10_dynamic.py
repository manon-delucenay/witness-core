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
from sostrades_core.execution_engine.sos_wrapp import SoSWrapp
import pandas as pd
import numpy as np


class Disc10(SoSWrapp):

    # ontology information
    _ontology_data = {
        'label': 'Disc10 discipline with dynamic inputs',
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
    DESC_IN = {
        'Model_Type': {'type': 'string', 'default': 'Linear',
                       'possible_values': ['Linear', 'Affine', 'Polynomial'],
                       'visibility': SoSWrapp.SHARED_VISIBILITY,
                       'namespace': 'ns_ac', 'structuring': True},
        'x': {'type': 'float',
              'visibility': SoSWrapp.SHARED_VISIBILITY,
              'namespace': 'ns_ac'},
        'a': {'type': 'float',
              'default': 1.,
              'visibility': SoSWrapp.SHARED_VISIBILITY,
              'namespace': 'ns_ac'}
    }
    DESC_OUT = {
        'y': {'type': 'float',
              'visibility': SoSWrapp.SHARED_VISIBILITY,
              'namespace': 'ns_ac'}
    }
    # ns_b is a new namespace defined for a dynamic variable in setup_sos_disciplines
    DYNAMIC_VAR_NAMESPACE_LIST = ['ns_b']

    def setup_sos_disciplines(self):
        dynamic_inputs = {}
        if 'Model_Type' in self.get_data_in():
            Model_Type = self.get_sosdisc_inputs('Model_Type')
            if Model_Type == 'Affine':
                dynamic_inputs.update({'b': {'type': 'float',
                                             'visibility': SoSWrapp.SHARED_VISIBILITY,
                                             'namespace': 'ns_b'}})
            elif Model_Type == 'Polynomial':
                dynamic_inputs.update(
                    {'b': {'type': 'float', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_b'}})
                dynamic_inputs.update({'power': {'type': 'float', 'default': 2.,
                                                 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_ac'}})
        self.add_inputs(dynamic_inputs)

    def run(self):
        input_dict = self.get_sosdisc_inputs()
        Model_Type = input_dict['Model_Type']
        x = input_dict['x']
        a = input_dict['a']
        if Model_Type == 'Linear':
            y = a * x
        elif Model_Type == 'Affine':
            b = input_dict['b']
            y = a * x + b
        elif Model_Type == 'Polynomial':
            b = input_dict['b']
            power = input_dict['power']
            y = a * x**power + b
        dict_values = {}
        dict_values['y'] = y
        # put new field value in data_out
        self.store_sos_outputs_values(dict_values)
