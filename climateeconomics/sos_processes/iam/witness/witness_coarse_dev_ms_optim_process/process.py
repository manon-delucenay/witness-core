'''
Copyright 2022 Airbus SAS
Modifications on 27/11/2023 Copyright 2023 Capgemini

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
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder


class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'WITNESS Coarse Dev Multi-Scenario Optimization Process',
        'description': '',
        'category': '',
        'version': '',
    }

    def get_builders(self):
        """
        # scenario build map
        scenario_map = {'input_name': 'scenario_list',

                        'input_ns': 'ns_scatter_scenario',
                        'output_name': 'scenario_name',
                        'scatter_ns': 'ns_scenario',
                        'gather_ns': 'ns_scatter_scenario',
                        'ns_to_update': ['ns_witness',
                                         'ns_functions',
                                         'ns_energy_mix',
                                         'ns_public',
                                         'ns_optim',
                                         'ns_flue_gas',
                                         'ns_energy_study',
                                         'ns_energy',
                                         'ns_carbon_capture',
                                         'ns_carbon_storage',
                                         'ns_land_use',
                                         'ns_renewable',
                                         'ns_fossil',
                                         'ns_ccs',
                                         'ns_resource',
                                         #'ns_ref',
                                         'ns_invest',
                                         'ns_agriculture',
                                         'ns_crop',
                                         'ns_forest',
                                         'ns_coal_resource',
                                         'ns_natural_gas_resource',
                                         'ns_oil_resource',
                                         'ns_uranium_resource'
                                         ]}

        self.ee.smaps_manager.add_build_map(
            'scenario_list', scenario_map)
        """
        builder_cdf_list = self.ee.factory.get_builder_from_process(
            'climateeconomics.sos_processes.iam.witness', 'witness_coarse_dev_optim_process')

        scatter_scenario_name = 'optimization scenarios'
        # modify namespaces defined in the child process
        self.ee.ns_manager.update_namespace_list_with_extra_ns(
            scatter_scenario_name, after_name=self.ee.study_name)

        # Add new namespaces needed for the scatter multiscenario
        ns_dict = {'ns_scatter_scenario': f'{self.ee.study_name}.{scatter_scenario_name}',
                   'ns_post_processing': f'{self.ee.study_name}.Post-processing',
                   'ns_ref': f'{self.ee.study_name}.{scatter_scenario_name}.NormalizationReferences'}

        self.ee.ns_manager.add_ns_def(ns_dict)

        multi_scenario = self.ee.factory.create_driver(
            'optimization scenarios', builder_cdf_list, flatten_subprocess=False
        )
        self.ee.post_processing_manager.add_post_processing_module_to_namespace('ns_post_processing',
                                                                                'climateeconomics.sos_wrapping.sos_wrapping_witness.post_proc_witness_ms.post_processing_witness_full')

        return multi_scenario
