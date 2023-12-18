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
from sostrades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from sostrades_core.study_manager.study_manager import StudyManager
import pandas as pd


class Study(StudyManager):

    def __init__(self, execution_engine=None):
        super().__init__(__file__, execution_engine=execution_engine)

    def setup_usecase(self):
        setup_data_list = []

        activation_df = pd.DataFrame(
            {'Business': ['Remy', 'Remy', 'Tomato_producer'],
             'product_list': ['Ratatouille', 'Tomato_Sauce', 'Tomato'],
             'CAPEX': [True, True, True],
             'Opex': [True, False, False]})

        values_dict = {
            f'{self.study_name}.Business.activation_df': activation_df}

        setup_data_list.append(values_dict)
        return setup_data_list


if '__main__' == __name__:
    uc_cls = Study()
    uc_cls.load_data()
    uc_cls.run()
