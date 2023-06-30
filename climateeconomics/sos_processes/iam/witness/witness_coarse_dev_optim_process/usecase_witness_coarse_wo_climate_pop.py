'''
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

from climateeconomics.sos_processes.iam.witness.witness_coarse_dev_optim_process.usecase_witness_optim_invest_distrib import Study as usecase_witness
from climateeconomics.core.tools.ClimateEconomicsStudyManager import ClimateEconomicsStudyManager

from pandas import DataFrame
from numpy import arange, linspace


class Study(ClimateEconomicsStudyManager):

    def __init__(self, run_usecase=False, execution_engine=None, year_start=2020, year_end=2100, time_step=1):
        super().__init__(__file__, run_usecase=run_usecase, execution_engine=execution_engine)
        self.year_start = year_start
        self.year_end = year_end
        self.time_step = time_step

    def setup_usecase(self):
        witness_uc = usecase_witness()
        witness_uc.study_name = self.study_name
        data_witness = witness_uc.setup_usecase()
        updated_data = {f'{self.study_name}.assumptions_dict': {'compute_damage_on_climate': False,
                                                                'activate_climate_effect_population': False,
                                                                'invest_co2_tax_in_renewables': False,
                                                                'compute_climate_impact_on_gdp': False
                                                               }}
        data_witness.append(updated_data)
        return data_witness


if '__main__' == __name__:
    uc_cls = Study(run_usecase=True)
    uc_cls.load_data()
    uc_cls.run()
    print('-----')