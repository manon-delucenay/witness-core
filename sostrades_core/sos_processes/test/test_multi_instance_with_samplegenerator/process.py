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
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder


class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'Test Multi Instance With Sample Generator (DriverEvaluator)',
        'description': '',
        'category': '',
        'version': '',
    }

    def get_builders(self):
        # simple 2-disc process NOT USING nested scatters coupled with a SampleGenerator

        # putting the ns_sampling in the same value as the driver will trigger
        # the coupling like in mono instance case
        self.ee.ns_manager.add_ns(
            'ns_sampling', f'{self.ee.study_name}.multi_scenarios')

        # multi scenario driver builder
        multi_scenarios = self.ee.factory.get_builder_from_process(repo='sostrades_core.sos_processes.test',
                                                                   mod_id='test_multi_instance_basic')
        # sample generator builder
        mod_cp = 'sostrades_core.execution_engine.disciplines_wrappers.sample_generator_wrapper.SampleGeneratorWrapper'
        cp_builder = self.ee.factory.get_builder_from_module('Sample_Generator', mod_cp)

        return multi_scenarios + [cp_builder]
