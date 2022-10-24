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
'''
mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8
'''
import unittest
from os.path import join, dirname
from pandas import read_csv
from pandas import DataFrame 
import numpy as np
from sos_trades_core.execution_engine.execution_engine import ExecutionEngine


class LaborMarketTestCase(unittest.TestCase):

    def setUp(self):
        '''
        Initialize third data needed for testing
        '''
        self.year_start = 2020
        self.year_end = 2100
        nb_per = round(self.year_end - self.year_start + 1)
        self.nb_per = nb_per
        self.years = np.arange(self.year_start, self.year_end+1)
        
        agrishare = 27.4
        indusshare = 21.7
        serviceshare = 50.9
        workforce_share = DataFrame({'years':self. years, 'Agriculture': agrishare, 
                                     'Industry': indusshare, 'Services': serviceshare})
        self.workforce_share = workforce_share
        data_dir = join(dirname(__file__), 'data')
        working_age_pop_df = read_csv(
                join(data_dir, 'workingage_population_df.csv'))
        working_age_pop_df.index = self.years
        self.working_age_pop_df = working_age_pop_df
        

    def test_labormarket_discipline(self):
        '''
        Check discipline setup and run
        '''
        name = 'Test'
        model_name = 'Labor Market'
        ee = ExecutionEngine(name)
        ns_dict = {'ns_public': f'{name}',
                   'ns_witness':  f'{name}'}
        ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_sectors.labor_market.labor_market_discipline.LaborMarketDiscipline'
        builder = ee.factory.get_builder_from_module(model_name, mod_path)

        ee.factory.set_builders_to_coupling_builder(builder)

        ee.configure()
        ee.display_treeview_nodes()
        inputs_dict = {f'{name}.year_start': self.year_start,
                       f'{name}.year_end': self.year_end,
                       f'{name}.{model_name}.workforce_share_per_sector': self.workforce_share, 
                       f'{name}.working_age_population_df': self.working_age_pop_df
                       }

        ee.load_study_from_input_dict(inputs_dict)
        ee.execute()
        disc = ee.dm.get_disciplines_with_name(
            f'{name}.{model_name}')[0]
        filter = disc.get_chart_filter_list()
        graph_list = disc.get_post_processing_list(filter)
#         for graph in graph_list:
#           graph.to_plotly().show()
    
    def test_changingworkforceshare_labormarket(self):
        #test with a decreasing share in agri 
        nb_per = len(self.years)
        indusshare = 21.7
        agri_year_start = 27.4
        agri = []
        agri.append(agri_year_start)
        for year in np.arange(1, nb_per):
            agri.append(agri[year - 1] * 0.99)
        service = np.array([100.0]*nb_per) - agri - indusshare
        #service = np.substract(total, agri)
        workforce_share = DataFrame({'years':self. years, 'Agriculture': agri, 
                                     'Industry': indusshare, 'Services': service})
        
        name = 'Test'
        model_name = 'Labor Market'
        ee = ExecutionEngine(name)
        ns_dict = {'ns_public': f'{name}',
                   'ns_witness':  f'{name}'}
        ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_sectors.labor_market.labor_market_discipline.LaborMarketDiscipline'
        builder = ee.factory.get_builder_from_module(model_name, mod_path)

        ee.factory.set_builders_to_coupling_builder(builder)

        ee.configure()
        ee.display_treeview_nodes()
        inputs_dict = {f'{name}.year_start': self.year_start,
                       f'{name}.year_end': self.year_end,
                       f'{name}.{model_name}.workforce_share_per_sector': workforce_share, 
                       f'{name}.working_age_population_df': self.working_age_pop_df
                       }

        ee.load_study_from_input_dict(inputs_dict)
        ee.execute()
        disc = ee.dm.get_disciplines_with_name(
            f'{name}.{model_name}')[0]
        filter = disc.get_chart_filter_list()
        graph_list = disc.get_post_processing_list(filter)
#         for graph in graph_list:
#             graph.to_plotly().show()
            