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
import unittest
from os.path import join, dirname
from pandas import read_csv
from sostrades_core.execution_engine.execution_engine import ExecutionEngine

class UraniumModelTestCase(unittest.TestCase):

    def setUp(self):
        '''
        Initialize third data needed for testing
        '''
        self.year_start = 2020
        self.year_end = 2100
        self.production_start=1970

        data_dir = join(dirname(__file__), 'data')

        self.energy_uranium_demand_df = read_csv(
            join(data_dir, 'all_demand_from_energy_mix.csv'))
        # part to adapt lenght to the year range

        self.energy_uranium_demand_df = self.energy_uranium_demand_df.loc[self.energy_uranium_demand_df['years']
                                                                    >= self.year_start]
        self.energy_uranium_demand_df= self.energy_uranium_demand_df.loc[self.energy_uranium_demand_df['years']
                                                                  <= self.year_end]

        self.param = {'resources_demand': self.energy_uranium_demand_df,
                      'year_start': self.year_start,
                      'year_end': self.year_end,
                      'production_start': self.production_start}

    def test_uranium_discipline(self):
        ''' 
        Check discipline setup and run
        '''
        name = 'Test'
        model_name = 'uranium_use'
        ee = ExecutionEngine(name)
        ns_dict = {'ns_public': f'{name}',
                   'ns_witness': f'{name}.{model_name}',
                   'ns_functions': f'{name}.{model_name}',
                   'ns_uranium_resource': f'{name}.{model_name}',
                   'ns_resource': f'{name}.{model_name}'}
        ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.core.core_resources.models.uranium_resource.uranium_resource_disc.UraniumResourceDiscipline'
        builder = ee.factory.get_builder_from_module(model_name, mod_path)

        ee.factory.set_builders_to_coupling_builder(builder)

        ee.configure()
        ee.display_treeview_nodes()

        inputs_dict = {f'{name}.year_start': self.year_start,
                       f'{name}.year_end': self.year_end,
                       f'{name}.{model_name}.resources_demand': self.energy_uranium_demand_df,
                       'production_start': self.production_start}
        ee.load_study_from_input_dict(inputs_dict)

        ee.execute()

        disc = ee.dm.get_disciplines_with_name(
            f'{name}.{model_name}')[0]
        filter = disc.get_chart_filter_list()
        graph_list = disc.get_post_processing_list(filter)
        #for graph in graph_list:
        #    graph.to_plotly().show()
if __name__ =="__main__" :
    unittest.main()