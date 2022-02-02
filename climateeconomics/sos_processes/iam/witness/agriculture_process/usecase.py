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


def update_dspace_dict_with(dspace_dict, name, value, lower, upper, activated_elem=None, enable_variable=True):
    if not isinstance(lower, (list, np.ndarray)):
        lower = [lower] * len(value)
    if not isinstance(upper, (list, np.ndarray)):
        upper = [upper] * len(value)

    if activated_elem is None:
        activated_elem = [True] * len(value)
    dspace_dict[name] = {'value': value,
                         'lower_bnd': lower, 'upper_bnd': upper, 'enable_variable': enable_variable, 'activated_elem': activated_elem}

    dspace_dict['dspace_size'] += len(value)


class Study(StudyManager):

    def __init__(self, year_start=2020, year_end=2100, time_step=1, name='.Agriculture', execution_engine=None):
        super().__init__(__file__, execution_engine=execution_engine)
        self.study_name = 'usecase'
        self.agriculture_name = name
        self.year_start = year_start
        self.year_end = year_end
        self.time_step = time_step
        self.nb_poles = 5

    def setup_usecase(self):

        setup_data_list = []

        years = np.arange(self.year_start, self.year_end + 1, 1)
        year_range = self.year_end - self.year_start + 1

        #population = np.array(np.linspace(7900, 8500, year_range))

        population = np.array([7886.69358, 7966.665211, 8045.375451, 8122.797867, 8198.756532, 8273.083818, 8345.689982, 8416.57613, 8485.795919, 8553.312856, 8619.058953, 8683.042395, 8745.257656,
                               8805.680119, 8864.337481, 8921.246891, 8976.395584, 9029.771873, 9081.354412, 9131.121464, 9179.083525, 9225.208209, 9269.477788, 9311.832053, 9352.201944, 9390.558602,
                               9426.867911, 9461.124288, 9493.330078, 9523.465887, 9551.506077, 9577.443894, 9601.291404, 9623.075287, 9642.80847, 9660.498856, 9676.158366, 9689.826469, 9701.54988,
                               9711.366041, 9719.318272, 9725.419042, 9729.702777, 9732.206794, 9732.922689, 9731.871402, 9729.064465, 9724.513081, 9718.249401, 9710.282554, 9700.610324, 9689.251038,
                               9676.243561, 9661.590658, 9645.329918, 9627.498797, 9608.104964, 9587.197508, 9564.828118, 9541.038722, 9515.888869, 9489.415825, 9461.693469, 9432.803085, 9402.775341,
                               9371.660258, 9339.478398, 9306.261187, 9272.043294, 9236.831993, 9200.632391, 9163.429244, 9125.227987, 9086.036337, 9045.87235, 9004.753844, 8962.700979, 8919.730768,
                               8875.855926, 8831.098444, 8785.553666])

        temperature = np.array(np.linspace(1.05, 5, year_range))
#         temperature = np.array(np.linspace(1.05, 1.05, year_range))

        temperature_df = pd.DataFrame(
            {"years": years, "temp_atmo": temperature})
        temperature_df.index = years

        population_df = pd.DataFrame(
            {"years": years, "population": population})
        population_df.index = years

        default_kg_to_m2 = {'red meat': 345,
                            'white meat': 16,
                            'milk': 8.95,
                            'eggs': 6.3,
                            'rice and maize': 2.9,
                            'potatoes': 0.88,
                            'fruits and vegetables': 0.8,
                            }
        default_kg_to_kcal = {'red meat': 2566,
                              'white meat': 1860,
                              'milk': 550,
                              'eggs': 1500,
                              'rice and maize': 1150,
                              'potatoes': 670,
                              'fruits and vegetables': 624,
                              }
        red_to_white_meat = np.linspace(0, 50, year_range)
        meat_to_vegetables = np.linspace(0, 50, year_range)
        red_to_white_meat_df = pd.DataFrame(
            {'years': years, 'red_to_white_meat_percentage': red_to_white_meat})
        meat_to_vegetables_df = pd.DataFrame(
            {'years': years, 'meat_to_vegetables_percentage': meat_to_vegetables})
        red_to_white_meat_df.index = years
        meat_to_vegetables_df.index = years
        self.red_to_white_meat_df = red_to_white_meat_df
        self.meat_to_vegetables_df = meat_to_vegetables_df

        diet_df = pd.DataFrame({'red meat': [11.02],
                                'white meat': [31.11],
                                'milk': [79.27],
                                'eggs': [9.68],
                                'rice and maize': [97.76],
                                'potatoes': [32.93],
                                'fruits and vegetables': [217.62],
                                })
        other = np.array(np.linspace(0.102, 0.102, year_range))

        # private values economics operator model
        agriculture_input = {}
        agriculture_input[self.study_name + '.year_start'] = self.year_start
        agriculture_input[self.study_name + '.year_end'] = self.year_end

        agriculture_input[self.study_name + self.agriculture_name +
                          '.diet_df'] = diet_df
        agriculture_input[self.study_name + self.agriculture_name +
                          '.kg_to_kcal_dict'] = default_kg_to_kcal
        agriculture_input[self.study_name + self.agriculture_name +
                          '.kg_to_m2_dict'] = default_kg_to_m2
        agriculture_input[self.study_name + self.agriculture_name +
                          '.red_to_white_meat'] = red_to_white_meat
        agriculture_input[self.study_name + self.agriculture_name +
                          '.meat_to_vegetables'] = meat_to_vegetables
        agriculture_input[self.study_name + self.agriculture_name +
                          '.other_use_agriculture'] = other

        agriculture_input[self.study_name +
                          '.population_df'] = population_df

        agriculture_input[self.study_name +
                          '.temperature_df'] = temperature_df

        setup_data_list.append(agriculture_input)

        red_to_white_meat_ctrl = np.linspace(15.0, 15.0, self.nb_poles)
        meat_to_vegetables_ctrl = np.linspace(15.0, 15.0, self.nb_poles)

        design_space_ctrl_dict = {}
        design_space_ctrl_dict['red_to_white_meat_ctrl'] = red_to_white_meat_ctrl
        design_space_ctrl_dict['meat_to_vegetables_ctrl'] = meat_to_vegetables_ctrl

        design_space_ctrl = pd.DataFrame(design_space_ctrl_dict)
        self.design_space_ctrl = design_space_ctrl

        return setup_data_list

    def setup_initial_design_variable(self):

        init_design_var_df = pd.DataFrame(
            columns=['red_to_white_meat_percentage', 'meat_to_vegetables_percentage'], index=arange(self.year_start, self.year_end + 1, self.time_step))

        init_design_var_df['red_to_white_meat_percentage'] = self.red_to_white_meat_df['red_to_white_meat_percentage']
        init_design_var_df['meat_to_vegetables_percentage'] = self.meat_to_vegetables_df['meat_to_vegetables_percentage']

        return init_design_var_df

    def setup_design_space(self):
            #-- energy optimization inputs
            # Design Space
        dim_a = len(
            self.red_to_white_meat_df['red_to_white_meat_percentage'].values)
        lbnd1 = [0.0] * dim_a
        ubnd1 = [100.0] * dim_a

        # Design variables:
        self.update_dspace_dict_with(
            'red_to_white_meat_array', self.red_to_white_meat_df['red_to_white_meat_percentage'].values, lbnd1, ubnd1)
        self.update_dspace_dict_with(
            'meat_to_vegetables_array', self.meat_to_vegetables_df['meat_to_vegetables_percentage'].values, lbnd1, ubnd1)

    def setup_design_space_ctrl_new(self):
        # Design Space
        #header = ['variable', 'value', 'lower_bnd', 'upper_bnd']
        ddict = {}
        ddict['dspace_size'] = 0

        # Design variables:
        update_dspace_dict_with(ddict, 'red_to_white_meat_ctrl',
                                self.design_space_ctrl['red_to_white_meat_ctrl'], 1.0, 100.0, activated_elem=[False, True, True, True, True, True, True])
        update_dspace_dict_with(ddict, 'meat_to_vegetables_ctrl',
                                self.design_space_ctrl['meat_to_vegetables_ctrl'], 1.0, 100.0, activated_elem=[False, True, True, True, True, True, True])

        return ddict


if '__main__' == __name__:
    uc_cls = Study()
    uc_cls.load_data()
    # uc_cls.execution_engine.display_treeview_nodes(display_variables=True)
    # uc_cls.execution_engine.set_debug_mode()
    uc_cls.run()

    # ppf = PostProcessingFactory()
    # for disc in uc_cls.execution_engine.root_process.sos_disciplines:
    #     filters = ppf.get_post_processing_filters_by_discipline(
    #         disc)
    #     graph_list = ppf.get_post_processing_by_discipline(
    #         disc, filters, as_json=False)

    #     for graph in graph_list:
    #         graph.to_plotly().show()