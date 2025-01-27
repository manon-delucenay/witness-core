'''
Copyright 2022 Airbus SAS
Modifications on 2023/06/29-2023/11/03 Copyright 2023 Capgemini

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

from pandas import read_csv

from climateeconomics.glossarycore import GlossaryCore
from sostrades_core.execution_engine.execution_engine import ExecutionEngine
from sostrades_core.tests.core.abstract_jacobian_unit_test import AbstractJacobianUnittest


class IndusEmissionsJacobianDiscTest(AbstractJacobianUnittest):
    #AbstractJacobianUnittest.DUMP_JACOBIAN = True
    # np.set_printoptions(threshold=np.inf)

    def setUp(self):

        self.name = 'Test'
        self.ee = ExecutionEngine(self.name)

    def analytic_grad_entry(self):
        return [
            self.test_carbon_emissions_analytic_grad
        ]

    def test_carbon_emissions_analytic_grad(self):

        self.model_name = 'indusemission'
        ns_dict = {'ns_witness': f'{self.name}',
                   'ns_public': f'{self.name}',
                   'ns_energy_mix': f'{self.name}',
                   'ns_ref': f'{self.name}',
                   'ns_ccs': f'{self.name}',
                   'ns_energy': f'{self.name}'}
        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_emissions.indus_emissions.indusemissions_discipline.IndusemissionsDiscipline'
        builder = self.ee.factory.get_builder_from_module(self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes()

        data_dir = join(dirname(__file__), 'data')
        year_start = 2020
        economics_df_all = read_csv(
            join(data_dir, 'economics_data_onestep.csv'))
        economics_df_y = economics_df_all[economics_df_all[GlossaryCore.Years] >= year_start][[
            GlossaryCore.Years, GlossaryCore.GrossOutput]]
        values_dict = {f'{self.name}.{GlossaryCore.EconomicsDfValue}': economics_df_y}

        self.ee.load_study_from_input_dict(values_dict)
        self.ee.execute()

        disc_techno = self.ee.root_process.proxy_disciplines[0].mdo_discipline_wrapp.mdo_discipline

        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_indus_emission_discipline.pkl',
                            discipline=disc_techno, step=1e-15, derr_approx='complex_step', local_data = disc_techno.local_data,
                            inputs=[f'{self.name}.{GlossaryCore.EconomicsDfValue}'],
                            outputs=[f'{self.name}.CO2_indus_emissions_df'])
