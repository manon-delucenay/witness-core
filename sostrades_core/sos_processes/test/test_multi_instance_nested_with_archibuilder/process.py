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
# mode: python; py-indent-offset: 4; tab-width: 8; coding:utf-8
#-- Generate test 1 process
import pandas as pd
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder

class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'Test Multi Instance Nested (DriverEvaluator) with Archi Builder',
        'description': '',
        'category': '',
        'version': '',
    }

    def get_builders(self):
        # archi builder business
        vb_builder_name_business = 'Business'
        architecture_df_business = pd.DataFrame(
            {'Parent': ['Business', 'Remy', 'Remy'],
             'Current': ['Remy', 'CAPEX', 'OPEX'],
             'Type': ['SumValueBlockDiscipline', 'SumValueBlockDiscipline', 'SumValueBlockDiscipline'],
             'Action': [('standard'),  ('standard'),  ('standard')],
             'Activation': [True, False, False]})
        builder_business = self.ee.factory.create_architecture_builder(
            vb_builder_name_business, architecture_df_business)

        # archi builder production
        vb_builder_name_production = 'Production'
        architecture_df_production = pd.DataFrame(
            {'Parent': ['Production', 'Production', 'Local', 'Abroad', 'Abroad'],
             'Current': ['Abroad', 'Local', 'Road', 'Road', 'Plane'],
             'Type': ['SumValueBlockDiscipline', 'SumValueBlockDiscipline', 'SumValueBlockDiscipline', 'SumValueBlockDiscipline', 'SumValueBlockDiscipline'],
             'Action': [('standard'),  ('standard'),  ('standard'),  ('standard'),  ('standard')],
             'Activation': [True, False, False, False, False]})
        builder_production = self.ee.factory.create_architecture_builder(
            vb_builder_name_production, architecture_df_production)

        # builders of the core process
        builder_list = [builder_production, builder_business]

        # create the inner ms driver
        inner_ms = self.ee.factory.create_driver(
            'inner_ms',  builder_list)

        # create an outer ms driver
        outer_ms = self.ee.factory.create_driver(
            'outer_ms', inner_ms)

        return outer_ms
