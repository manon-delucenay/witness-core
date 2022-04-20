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
import numpy as np
import pandas as pd
import scipy.interpolate as sc
from numpy import asarray, arange, array

from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from energy_models.core.energy_mix_study_manager import EnergyMixStudyManager
from energy_models.core.stream_type.energy_models.biomass_dry import BiomassDry
from energy_models.core.energy_process_builder import INVEST_DISCIPLINE_OPTIONS,\
    INVEST_DISCIPLINE_DEFAULT

DEFAULT_TECHNOLOGIES_LIST = ['Crop', 'Forest']
TECHNOLOGIES_LIST_FOR_OPT = ['Crop', 'Forest']


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


class Study(EnergyMixStudyManager):
    def __init__(self, year_start=2020, year_end=2100, time_step=1, technologies_list=TECHNOLOGIES_LIST_FOR_OPT,
                 bspline=True,  main_study=True, execution_engine=None, invest_discipline=INVEST_DISCIPLINE_DEFAULT):
        super().__init__(__file__, technologies_list=technologies_list,
                         main_study=main_study, execution_engine=execution_engine, invest_discipline=invest_discipline)
        self.year_start = year_start
        self.year_end = year_end
        self.years = np.arange(self.year_start, self.year_end + 1)
        self.energy_name = None
        self.bspline = bspline
        self.nb_poles = 8
        self.additional_ns = ''

    def get_investments(self):
        invest_biomass_dry_mix_dict = {}
        l_ctrl = np.arange(0, 8)

        if 'Forest' in self.technologies_list:
            invest_biomass_dry_mix_dict['Forest'] = [
                (1 + 0.03)**i for i in l_ctrl]

        if 'Crop' in self.technologies_list:
            invest_biomass_dry_mix_dict['Crop'] = np.array([
                1.0, 1.0, 0.8, 0.6, 0.4, 0.4, 0.4, 0.4])

        if self.bspline:
            invest_biomass_dry_mix_dict['years'] = self.years

            for techno in self.technologies_list:
                invest_biomass_dry_mix_dict[techno], _ = self.invest_bspline(
                    invest_biomass_dry_mix_dict[techno], len(self.years))

        biomass_dry_mix_invest_df = pd.DataFrame(invest_biomass_dry_mix_dict)

        return biomass_dry_mix_invest_df

    def setup_usecase(self):
        self.agri_techo_list = ['Forest']
        agriculture_mix = 'AgricultureMix'
        energy_name = f'{agriculture_mix}'
        years = np.arange(self.year_start, self.year_end + 1)
        # reference_data_name = 'Reference_aircraft_data'
        self.energy_prices = pd.DataFrame({'years': years,
                                           'electricity': 16.0})
        year_range = self.year_end - self.year_start + 1

        temperature = np.array(np.linspace(1.05, 5.0, year_range))
        temperature_df = pd.DataFrame(
            {"years": years, "temp_atmo": temperature})
        temperature_df.index = years

        population = np.array(np.linspace(7800.0, 9000.0, year_range))
        population_df = pd.DataFrame(
            {"years": years, "population": population})
        population_df.index = years

        red_meat_percentage = np.linspace(6.82, 1, year_range)
        white_meat_percentage = np.linspace(13.95, 5, year_range)
        self.red_meat_percentage = pd.DataFrame({
            'years': years,
            'red_meat_percentage': red_meat_percentage})
        self.white_meat_percentage = pd.DataFrame({
            'years': years,
            'white_meat_percentage': white_meat_percentage})

        diet_df = pd.DataFrame({'red meat': [11.02],
                                'white meat': [31.11],
                                'milk': [79.27],
                                'eggs': [9.68],
                                'rice and maize': [97.76],
                                'potatoes': [32.93],
                                'fruits and vegetables': [217.62],
                                })
        other = np.array(np.linspace(0.102, 0.102, year_range))

        crop_invest = np.linspace(0.5, 0.25, year_range)
        self.crop_investment = pd.DataFrame(
            {'years': years, 'investment': crop_invest})

        self.margin = pd.DataFrame(
            {'years': years, 'margin': np.ones(len(years)) * 110.0})
        # From future of hydrogen
        self.transport = pd.DataFrame(
            {'years': years, 'transport': np.ones(len(years)) * 7.6})

        self.energy_carbon_emissions = pd.DataFrame(
            {'years': years, 'biomass_dry': - 0.64 / 4.86, 'solid_fuel': 0.64 / 4.86, 'electricity': 0.0, 'methane': 0.123 / 15.4, 'syngas': 0.0, 'hydrogen.gaseous_hydrogen': 0.0, 'crude oil': 0.02533})

        deforestation_surface = np.linspace(10, 5, year_range)
        self.deforestation_surface_df = pd.DataFrame(
            {"years": years, "deforested_surface": deforestation_surface})

        forest_invest = np.linspace(5, 8, year_range)

        self.forest_invest_df = pd.DataFrame(
            {"years": years, "forest_investment": forest_invest})
        mw_invest = np.linspace(1, 4, year_range)
        uw_invest = np.linspace(0, 1, year_range)
        self.mw_invest_df = pd.DataFrame(
            {"years": years, "investment": mw_invest})
        self.uw_invest_df = pd.DataFrame(
            {"years": years, "investment": uw_invest})

        co2_taxes_year = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050]
        co2_taxes = [14.86, 17.22, 20.27,
                     29.01,  34.05,   39.08,  44.69,   50.29]
        func = sc.interp1d(co2_taxes_year, co2_taxes,
                           kind='linear', fill_value='extrapolate')

        self.co2_taxes = pd.DataFrame(
            {'years': years, 'CO2_tax': func(years)})

        values_dict = {f'{self.study_name}.year_start': self.year_start,
                       f'{self.study_name}.year_end': self.year_end,
                       f'{self.study_name}.{energy_name}.technologies_list': self.technologies_list,
                       f'{self.study_name}.margin': self.margin,
                       f'{self.study_name}.transport_cost': self.transport,
                       f'{self.study_name}.transport_margin': self.margin,
                       f'{self.study_name}.CO2_taxes': self.co2_taxes,
                       f'{self.study_name}.{energy_name}.Crop.diet_df': diet_df,
                       f'{self.study_name}.{energy_name}.Crop.red_meat_percentage': self.red_meat_percentage,
                       f'{self.study_name}.{energy_name}.Crop.white_meat_percentage': self.white_meat_percentage,
                       f'{self.study_name}.{energy_name}.Crop.other_use_crop': other,
                       f'{self.study_name + self.additional_ns}.crop_investment': self.crop_investment,
                       }
        if self.main_study:
            values_dict.update({
                f'{self.study_name}.deforestation_surface': self.deforestation_surface_df,
                f'{self.study_name + self.additional_ns}.forest_investment': self.forest_invest_df,
                f'{self.study_name + self.additional_ns}.managed_wood_investment': self.mw_invest_df,
                f'{self.study_name + self.additional_ns}.unmanaged_wood_investment': self.uw_invest_df,
                f'{self.study_name}.population_df': population_df,
                f'{self.study_name}.temperature_df': temperature_df,
            })
        else:
            self.update_dv_arrays()

        red_meat_percentage_ctrl = np.linspace(6.82, 6.82, self.nb_poles)
        white_meat_percentage_ctrl = np.linspace(13.95, 13.95, self.nb_poles)
        deforestation_surface_ctrl = np.linspace(10.0, 5.0, self.nb_poles)
        forest_investment_array_mix = np.linspace(5.0, 8.0, self.nb_poles)
        crop_investment_array_mix = np.linspace(1.0, 1.5, self.nb_poles)
        managed_wood_investment_array_mix = np.linspace(
            2.0, 3.0, self.nb_poles)
        unmanaged_wood_investment_array_mix = np.linspace(
            4.0, 5.0, self.nb_poles)

        design_space_ctrl_dict = {}
        design_space_ctrl_dict['red_meat_percentage_ctrl'] = red_meat_percentage_ctrl
        design_space_ctrl_dict['white_meat_percentage_ctrl'] = white_meat_percentage_ctrl
        design_space_ctrl_dict['deforested_surface_ctrl'] = deforestation_surface_ctrl
        design_space_ctrl_dict['forest_investment_array_mix'] = forest_investment_array_mix
        design_space_ctrl_dict['crop_investment_array_mix'] = crop_investment_array_mix
        design_space_ctrl_dict['managed_wood_investment_array_mix'] = managed_wood_investment_array_mix
        design_space_ctrl_dict['unmanaged_wood_investment_array_mix'] = unmanaged_wood_investment_array_mix

        design_space_ctrl = pd.DataFrame(design_space_ctrl_dict)
        self.design_space_ctrl = design_space_ctrl
        self.dspace = self.setup_design_space_ctrl_new()

        return [values_dict]

    def setup_design_space_ctrl_new(self):
        # Design Space
        # header = ['variable', 'value', 'lower_bnd', 'upper_bnd']
        ddict = {}
        ddict['dspace_size'] = 0

        # Design variables
        # -----------------------------------------
        # Crop related
        update_dspace_dict_with(ddict, 'red_meat_percentage_ctrl',
                                list(self.design_space_ctrl['red_meat_percentage_ctrl'].values), [1.0] * self.nb_poles, [10.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)
        update_dspace_dict_with(ddict, 'white_meat_percentage_ctrl',
                                list(self.design_space_ctrl['white_meat_percentage_ctrl'].values), [5.0] * self.nb_poles, [20.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)
        update_dspace_dict_with(ddict, 'crop_investment_array_mix',
                                list(self.design_space_ctrl['crop_investment_array_mix'].values), [1.0e-6] * self.nb_poles, [3000.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)

        # -----------------------------------------
        # Forest related
        update_dspace_dict_with(ddict, 'deforested_surface_ctrl',
                                list(self.design_space_ctrl['deforested_surface_ctrl'].values), [0.0] * self.nb_poles, [100.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)

        update_dspace_dict_with(ddict, 'forest_investment_array_mix',
                                list(self.design_space_ctrl['forest_investment_array_mix'].values), [1.0e-6] * self.nb_poles, [3000.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)

        update_dspace_dict_with(ddict, 'managed_wood_investment_array_mix',
                                list(self.design_space_ctrl['managed_wood_investment_array_mix'].values), [1.0e-6] * self.nb_poles, [3000.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)

        update_dspace_dict_with(ddict, 'unmanaged_wood_investment_array_mix',
                                list(self.design_space_ctrl['unmanaged_wood_investment_array_mix'].values), [1.0e-6] * self.nb_poles, [3000.0] * self.nb_poles, activated_elem=[True] * self.nb_poles)

        return ddict


if '__main__' == __name__:
    uc_cls = Study(main_study=True,
                   technologies_list=DEFAULT_TECHNOLOGIES_LIST)
    uc_cls.load_data()
    uc_cls.run()
    ppf = PostProcessingFactory()
    for disc in uc_cls.execution_engine.root_process.sos_disciplines:
        filters = ppf.get_post_processing_filters_by_discipline(
            disc)
        graph_list = ppf.get_post_processing_by_discipline(
            disc, filters, as_json=False)

        # for graph in graph_list:
        #     graph.to_plotly().show()
