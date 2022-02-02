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
from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from sos_trades_core.study_manager.study_manager import StudyManager

from pathlib import Path
from os.path import join, dirname
from numpy import asarray, arange, array
import pandas as pd
import numpy as np
from sos_trades_core.execution_engine.func_manager.func_manager import FunctionManager
from sos_trades_core.execution_engine.func_manager.func_manager_disc import FunctionManagerDisc
from climateeconomics.core.tools.ClimateEconomicsStudyManager import ClimateEconomicsStudyManager

INEQ_CONSTRAINT = FunctionManagerDisc.INEQ_CONSTRAINT
OBJECTIVE = FunctionManagerDisc.OBJECTIVE
AGGR_TYPE = FunctionManagerDisc.AGGR_TYPE
AGGR_TYPE_SMAX = FunctionManager.AGGR_TYPE_SMAX
AGGR_TYPE_SUM = FunctionManager.AGGR_TYPE_SUM


def update_dspace_with(dspace_dict, name, value, lower, upper):
    ''' type(value) has to be ndarray
    '''
    if not isinstance(lower, (list, np.ndarray)):
        lower = [lower] * len(value)
    if not isinstance(upper, (list, np.ndarray)):
        upper = [upper] * len(value)
    dspace_dict['variable'].append(name)
    dspace_dict['value'].append(value.tolist())
    dspace_dict['lower_bnd'].append(lower)
    dspace_dict['upper_bnd'].append(upper)
    dspace_dict['dspace_size'] += len(value)


class Study(ClimateEconomicsStudyManager):

    def __init__(self, year_start=2020, year_end=2100, time_step=1, execution_engine=None):
        super().__init__(__file__, execution_engine=execution_engine)
        self.study_name = 'usecase'

        self.all_resource_name = '.All_resources'

        self.year_start = year_start
        self.year_end = year_end
        self.time_step = time_step
        self.nb_poles = 5

    def setup_usecase(self):

        setup_data_list = []

        # input of year start and year end:
        coal_input = {}
        coal_input[self.study_name + '.year_start'] = self.year_start
        coal_input[self.study_name + '.year_end'] = self.year_end

        oil_input = {}
        oil_input[self.study_name + '.year_start'] = self.year_start
        oil_input[self.study_name + '.year_end'] = self.year_end

        gas_input = {}
        gas_input[self.study_name + '.year_start'] = self.year_start
        gas_input[self.study_name + '.year_end'] = self.year_end

        uranium_input = {}
        uranium_input[self.study_name + '.year_start'] = self.year_start
        uranium_input[self.study_name + '.year_end'] = self.year_end

        resource_input = {}
        resource_input[self.study_name + '.year_start'] = self.year_start
        resource_input[self.study_name + '.year_end'] = self.year_end

        year_range = self.year_end - self.year_start
        years = arange(self.year_start, self.year_end + 1, 1)

        global_data_dir = join(Path(__file__).parents[4], 'data')

        setup_data_list.append(coal_input)
        setup_data_list.append(oil_input)
        setup_data_list.append(gas_input)
        setup_data_list.append(uranium_input)

        # ALL_RESOURCE
        data_dir_resource = join(
            dirname(dirname(dirname(dirname(dirname(__file__))))), 'tests', 'data')
        Non_modeled_resource_price = pd.read_csv(
            join(data_dir_resource, 'resource_data_price.csv'))
        Non_modeled_resource_price.index = Non_modeled_resource_price['years']
        resource_input[self.study_name + self.all_resource_name +
                       '.non_modeled_resource_price'] = Non_modeled_resource_price
        setup_data_list.append(resource_input)
        resource_demand = pd.read_csv(
            join(data_dir_resource, 'all_demand_from_energy_mix.csv'))

        resource_demand = resource_demand.loc[resource_demand['years']
                                              >= self.year_start]
        resource_demand = resource_demand.loc[resource_demand['years']
                                              <= self.year_end]
        resource_input[self.study_name +
                       self.all_resource_name + '.All_Demand'] = resource_demand
        setup_data_list.append(resource_input)

        return setup_data_list


if '__main__' == __name__:
    uc_cls = Study()
    uc_cls.load_data()
    uc_cls.execution_engine.set_debug_mode()
    uc_cls.run()
    uc_cls.execution_engine.display_treeview_nodes(True)

    ppf = PostProcessingFactory()
    for disc in uc_cls.execution_engine.root_process.sos_disciplines:
        filters = ppf.get_post_processing_filters_by_discipline(
            disc)
        graph_list = ppf.get_post_processing_by_discipline(
            disc, filters, as_json=False)

        for graph in graph_list:
            graph.to_plotly().show()