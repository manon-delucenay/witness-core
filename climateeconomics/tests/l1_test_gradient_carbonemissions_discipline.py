'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/06-2023/11/03 Copyright 2023 Capgemini

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

from os.path import join, dirname

import numpy as np
import pandas as pd
from pandas import read_csv

from climateeconomics.glossarycore import GlossaryCore
from energy_models.core.stream_type.carbon_models.carbon_dioxyde import CO2
from sostrades_core.execution_engine.execution_engine import ExecutionEngine
from sostrades_core.tests.core.abstract_jacobian_unit_test import AbstractJacobianUnittest


class CarbonEmissionsJacobianDiscTest(AbstractJacobianUnittest):
    # AbstractJacobianUnittest.DUMP_JACOBIAN = True
    # np.set_printoptions(threshold=np.inf)

    def setUp(self):

        self.name = 'Test'
        self.ee = ExecutionEngine(self.name)

    def analytic_grad_entry(self):
        return [
            self.test_carbon_emissions_analytic_grad,
            self.test_co2_objective_limit_grad
        ]

    def test_carbon_emissions_analytic_grad(self):

        self.model_name = 'carbonemission'
        ns_dict = {'ns_witness': f'{self.name}',
                   'ns_public': f'{self.name}',
                   'ns_energy_mix': f'{self.name}',
                   'ns_ref': f'{self.name}',
                   'ns_ccs': f'{self.name}',
                   'ns_energy': f'{self.name}'}
        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_witness.carbonemissions.carbonemissions_discipline.CarbonemissionsDiscipline'
        builder = self.ee.factory.get_builder_from_module(
            self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes()

        data_dir = join(dirname(__file__), 'data')

        economics_df_all = read_csv(
            join(data_dir, 'economics_data_onestep.csv'))
        energy_supply_df_all = read_csv(
            join(data_dir, 'energy_supply_data_onestep.csv'))
        year_start = 2020
        economics_df_y = economics_df_all[economics_df_all[GlossaryCore.Years] >= year_start][[
            GlossaryCore.Years, GlossaryCore.GrossOutput]]
        energy_supply_df_y = energy_supply_df_all[energy_supply_df_all[GlossaryCore.Years] >= year_start][[
            GlossaryCore.Years, 'total_CO2_emitted']]
        energy_supply_df_y[GlossaryCore.Years] = energy_supply_df_all[GlossaryCore.Years]
        energy_supply_df_y = energy_supply_df_y.rename(
            columns={'total_CO2_emitted': GlossaryCore.TotalCO2Emissions})

        co2_emissions_ccus_Gt = pd.DataFrame()
        co2_emissions_ccus_Gt[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        co2_emissions_ccus_Gt['carbon_storage Limited by capture (Gt)'] = 0.02

        CO2_emissions_by_use_sources = pd.DataFrame()
        CO2_emissions_by_use_sources[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        CO2_emissions_by_use_sources['CO2 from energy mix (Gt)'] = 0.0
        CO2_emissions_by_use_sources['carbon_capture from energy mix (Gt)'] = 0.0
        CO2_emissions_by_use_sources['Total CO2 by use (Gt)'] = 20.0
        CO2_emissions_by_use_sources['Total CO2 from Flue Gas (Gt)'] = 3.2

        CO2_emissions_by_use_sinks = pd.DataFrame()
        CO2_emissions_by_use_sinks[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        CO2_emissions_by_use_sinks[f'{CO2.name} removed by energy mix (Gt)'] = 0.0

        co2_emissions_needed_by_energy_mix = pd.DataFrame()
        co2_emissions_needed_by_energy_mix[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        co2_emissions_needed_by_energy_mix[
            'carbon_capture needed by energy mix (Gt)'] = 0.0
        # put manually the index
        years = np.arange(year_start, 2101)
        economics_df_y.index = years
        energy_supply_df_y.index = years
        co2_emissions_ccus_Gt.index = years
        CO2_emissions_by_use_sources.index = years
        CO2_emissions_by_use_sinks.index = years
        co2_emissions_needed_by_energy_mix.index = years

        CO2_emitted_forest = pd.DataFrame()
        emission_forest = np.linspace(0.01, 0.10, len(years))
        cum_emission = np.cumsum(emission_forest) + 3.21
        CO2_emitted_forest[GlossaryCore.Years] = years
        CO2_emitted_forest['emitted_CO2_evol_cumulative'] = cum_emission

        values_dict = {f'{self.name}.{GlossaryCore.EconomicsDfValue}': economics_df_y,
                       f'{self.name}.{GlossaryCore.CO2EmissionsGtValue}': energy_supply_df_y,
                       f'{self.name}.CO2_land_emissions': CO2_emitted_forest,
                       f'{self.name}.co2_emissions_ccus_Gt': co2_emissions_ccus_Gt,
                       f'{self.name}.CO2_emissions_by_use_sources': CO2_emissions_by_use_sources,
                       f'{self.name}.CO2_emissions_by_use_sinks': CO2_emissions_by_use_sinks,
                       f'{self.name}.co2_emissions_needed_by_energy_mix': co2_emissions_needed_by_energy_mix}

        self.ee.load_study_from_input_dict(values_dict)
        self.ee.execute()

        disc_techno = self.ee.root_process.proxy_disciplines[0].mdo_discipline_wrapp.mdo_discipline

        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_carbon_emission_discipline.pkl',
                            discipline=disc_techno, step=1e-15, derr_approx='complex_step', local_data = disc_techno.local_data,
                            inputs=[f'{self.name}.{GlossaryCore.EconomicsDfValue}',
                                    f'{self.name}.CO2_emissions_by_use_sources',
                                    f'{self.name}.CO2_land_emissions',
                                    f'{self.name}.CO2_emissions_by_use_sinks', f'{self.name}.co2_emissions_needed_by_energy_mix', f'{self.name}.co2_emissions_ccus_Gt'],
                            outputs=[f'{self.name}.{GlossaryCore.CO2EmissionsDfValue}',
                                     f'{self.name}.CO2_objective', f'{self.name}.{GlossaryCore.CO2EmissionsGtValue}'])

    def test_co2_objective_limit_grad(self):

        self.model_name = 'carbonemission'
        ns_dict = {'ns_witness': f'{self.name}',
                   'ns_public': f'{self.name}',
                   'ns_energy_mix': f'{self.name}',
                   'ns_ref': f'{self.name}',
                   'ns_ccs': f'{self.name}',
                   'ns_energy': f'{self.name}'}
        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_witness.carbonemissions.carbonemissions_discipline.CarbonemissionsDiscipline'
        builder = self.ee.factory.get_builder_from_module(
            self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes()

        data_dir = join(dirname(__file__), 'data')

        economics_df_all = read_csv(
            join(data_dir, 'economics_data_onestep.csv'))
        energy_supply_df_all = read_csv(
            join(data_dir, 'energy_supply_data_onestep.csv'))

        economics_df_y = economics_df_all[economics_df_all[GlossaryCore.Years] >= 2020][[
            GlossaryCore.Years, GlossaryCore.GrossOutput]]
        energy_supply_df_y = energy_supply_df_all[energy_supply_df_all[GlossaryCore.Years] >= 2020][[
            GlossaryCore.Years, 'total_CO2_emitted']]
        energy_supply_df_y[GlossaryCore.Years] = energy_supply_df_all[GlossaryCore.Years]
        energy_supply_df_y = energy_supply_df_y.rename(
            columns={'total_CO2_emitted': GlossaryCore.TotalCO2Emissions})
        co2_emissions_ccus_Gt = pd.DataFrame()
        co2_emissions_ccus_Gt[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        co2_emissions_ccus_Gt['carbon_storage Limited by capture (Gt)'] = 0.02

        CO2_emissions_by_use_sources = pd.DataFrame()
        CO2_emissions_by_use_sources[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        CO2_emissions_by_use_sources['CO2 from energy mix (Gt)'] = 0.0
        CO2_emissions_by_use_sources['carbon_capture from energy mix (Gt)'] = 0.0
        CO2_emissions_by_use_sources['Total CO2 by use (Gt)'] = 20.0
        CO2_emissions_by_use_sources['Total CO2 from Flue Gas (Gt)'] = 3.2

        CO2_emissions_by_use_sinks = pd.DataFrame()
        CO2_emissions_by_use_sinks[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        CO2_emissions_by_use_sinks[f'{CO2.name} removed by energy mix (Gt)'] = 0.0

        co2_emissions_needed_by_energy_mix = pd.DataFrame()
        co2_emissions_needed_by_energy_mix[GlossaryCore.Years] = energy_supply_df_y[GlossaryCore.Years]
        co2_emissions_needed_by_energy_mix[
            'carbon_capture needed by energy mix (Gt)'] = 0.0
        # put manually the index
        years = np.arange(2020, 2101)
        economics_df_y.index = years
        energy_supply_df_y.index = years
        energy_supply_df_y[GlossaryCore.TotalCO2Emissions] = np.linspace(
            0, -3000, len(years))

        CO2_emitted_forest = pd.DataFrame()
        emission_forest = np.linspace(0.04, 0.04, len(years))
        cum_emission = np.cumsum(emission_forest) + 3.21
        CO2_emitted_forest[GlossaryCore.Years] = years
        CO2_emitted_forest['emitted_CO2_evol_cumulative'] = cum_emission

        values_dict = {f'{self.name}.{GlossaryCore.EconomicsDfValue}': economics_df_y,
                       f'{self.name}.{GlossaryCore.CO2EmissionsGtValue}': energy_supply_df_y,
                       f'{self.name}.CO2_land_emissions': CO2_emitted_forest,
                       f'{self.name}.co2_emissions_ccus_Gt': co2_emissions_ccus_Gt,
                       f'{self.name}.CO2_emissions_by_use_sources': CO2_emissions_by_use_sources,
                       f'{self.name}.CO2_emissions_by_use_sinks': CO2_emissions_by_use_sinks,
                       f'{self.name}.co2_emissions_needed_by_energy_mix': co2_emissions_needed_by_energy_mix}

        self.ee.load_study_from_input_dict(values_dict)
        self.ee.execute()

        disc_techno = self.ee.root_process.proxy_disciplines[0].mdo_discipline_wrapp.mdo_discipline

        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_co2_objective_limit.pkl',
                            discipline=disc_techno, step=1e-15, derr_approx='complex_step', local_data = disc_techno.local_data,
                            inputs=[f'{self.name}.{GlossaryCore.EconomicsDfValue}',
                                    f'{self.name}.CO2_emissions_by_use_sources',
                                    f'{self.name}.CO2_land_emissions',
                                    f'{self.name}.CO2_emissions_by_use_sinks', f'{self.name}.co2_emissions_needed_by_energy_mix', f'{self.name}.co2_emissions_ccus_Gt'],
                            outputs=[f'{self.name}.{GlossaryCore.CO2EmissionsDfValue}',
                                     f'{self.name}.CO2_objective', f'{self.name}.{GlossaryCore.CO2EmissionsGtValue}'])
