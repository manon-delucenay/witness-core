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
from sostrades_core.study_manager.study_manager import StudyManager
import pandas as pd


class Study(StudyManager):

    def __init__(self, execution_engine=None):
        super().__init__(__file__, execution_engine=execution_engine)

    def setup_usecase(self):
        setup_data_list = []

        driver_name = 'multi_actors'
        dict_values = {}
        dict_values[f'{self.study_name}.{driver_name}.builder_mode'] = 'multi_instance'
        dict_values[f'{self.study_name}.{driver_name}.scenario_df'] = pd.DataFrame({'selected_scenario': [True,
                                                                                                          True],
                                                                                    'scenario_name': ['actor_1',
                                                                                                      'actor_2']})
        setup_data_list.append(dict_values)
        constant1 = 10
        constant2 = 20
        power1 = 2
        power2 = 3
        private_val = {}
        private_val[f'{self.study_name}.{driver_name}.actor_1.Disc2.constant'] = constant1
        private_val[f'{self.study_name}.{driver_name}.actor_1.Disc2.power'] = power1
        private_val[f'{self.study_name}.{driver_name}.actor_2.Disc2.constant'] = constant2
        private_val[f'{self.study_name}.{driver_name}.actor_2.Disc2.power'] = power2
        x1 = 2
        a1 = 3
        b1 = 4
        x2 = 4
        a2 = 6
        b2 = 2
        private_val[f'{self.study_name}.{driver_name}.actor_1.x'] = x1
        private_val[f'{self.study_name}.{driver_name}.actor_2.x'] = x2
        private_val[f'{self.study_name}.{driver_name}.actor_1.Disc1.a'] = a1
        private_val[f'{self.study_name}.{driver_name}.actor_2.Disc1.a'] = a2
        private_val[f'{self.study_name}.{driver_name}.actor_1.Disc1.b'] = b1
        private_val[f'{self.study_name}.{driver_name}.actor_2.Disc1.b'] = b2
        setup_data_list.append(private_val)
        return setup_data_list


if '__main__' == __name__:
    uc_cls = Study()
    uc_cls.load_data()
    uc_cls.run()
