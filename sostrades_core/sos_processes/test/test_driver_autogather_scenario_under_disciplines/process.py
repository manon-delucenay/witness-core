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
# -- Generate test 2 process
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder


class ProcessBuilder(BaseProcessBuilder):
    # ontology information
    _ontology_data = {
        'label': 'Core Test Display Treeview Autogather with Group Scenarios Under Disciplines Process',
        'description': '',
        'category': '',
        'version': '',
    }

    def get_builders(self):
        # instantiate factory by getting builder from process
        cls_list = self.ee.factory.get_builder_from_process(repo='sostrades_core.sos_processes.test',
                                                            mod_id='test_disc1_disc2_coupling')

        multi_scenarios = self.ee.factory.create_driver(
            'multi_scenarios', cls_list, display_options={'autogather': True,
                                                          'group_scenarios_under_disciplines': True})
        return multi_scenarios
