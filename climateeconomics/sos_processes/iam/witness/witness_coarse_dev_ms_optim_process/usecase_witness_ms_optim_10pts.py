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
from os.path import join, dirname

import numpy as np

from climateeconomics.core.tools.ClimateEconomicsStudyManager import ClimateEconomicsStudyManager
from climateeconomics.sos_processes.iam.witness.witness_coarse_dev_optim_process.usecase_witness_optim_invest_distrib import \
    Study as witness_optim_usecase
from sostrades_core.tools.post_processing.post_processing_factory import PostProcessingFactory


class Study(ClimateEconomicsStudyManager):

    def __init__(self, bspline=False, run_usecase=False, execution_engine=None):
        super().__init__(__file__, run_usecase=run_usecase, execution_engine=execution_engine)
        self.bspline = bspline
        self.data_dir = join(dirname(__file__), 'data')

    def setup_usecase(self):
        witness_ms_usecase = witness_optim_usecase(
            execution_engine=self.execution_engine)

        self.scatter_scenario = 'optimization scenarios'
        # Set public values at a specific namespace
        witness_ms_usecase.study_name = f'{self.study_name}.{self.scatter_scenario}'

        values_dict = {}
        scenario_list = []
        alpha_list = np.linspace(5, 95, 10, endpoint=True) / 100.0
        for alpha_i in alpha_list:
            scenario_i = 'scenario_\u03B1=%.2f' % alpha_i
            scenario_i = scenario_i.replace('.', ',')
            scenario_list.append(scenario_i)
            values_dict[f'{self.study_name}.{self.scatter_scenario}.{scenario_i}.{witness_ms_usecase.optim_name}.{witness_ms_usecase.coupling_name}.{witness_ms_usecase.extra_name}.alpha'] = alpha_i

        values_dict[f'{self.study_name}.{self.scatter_scenario}.scenario_list'] = scenario_list
        values_dict[f'{self.study_name}.epsilon0'] = 1.0
        values_dict[f'{self.study_name}.n_subcouplings_parallel'] = 10
        for scenario in scenario_list:
            scenarioUseCase = witness_optim_usecase(
                bspline=self.bspline, execution_engine=self.execution_engine)
            scenarioUseCase.optim_name = f'{scenario}.{scenarioUseCase.optim_name}'
            scenarioUseCase.study_name = witness_ms_usecase.study_name
            scenarioData = scenarioUseCase.setup_usecase()

            for dict_data in scenarioData:
                values_dict.update(dict_data)
        year_start = scenarioUseCase.year_start
        year_end = scenarioUseCase.year_end
        years = np.arange(year_start, year_end + 1)

        values_dict[f'{self.study_name}.{self.scatter_scenario}.NormalizationReferences.liquid_hydrogen_percentage'] = np.concatenate((np.ones(5)/1e-4,np.ones(len(years)-5)/4), axis=None)
        values_dict[f'{self.study_name}.{self.scatter_scenario}.builder_mode']= 'multi_instance'

        return values_dict


if '__main__' == __name__:
    uc_cls = Study(run_usecase=True)
    uc_cls.load_data()
    uc_cls.run()

    post_processing_factory = PostProcessingFactory()
    post_processing_factory.get_post_processing_by_namespace(
        uc_cls.execution_engine, f'{uc_cls.study_name}.Post-processing', [])
#     all_post_processings = post_processing_factory.get_all_post_processings(
#         uc_cls.execution_engine, False, as_json=False, for_test=False)
#
#     for namespace, post_proc_list in all_post_processings.items():
#         for chart in post_proc_list:
#             chart.to_plotly().show()
