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
from sos_trades_core.study_manager.study_manager import StudyManager
from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from climateeconomics.sos_processes.iam.witness.witness_optim_sub_process.usecase_witness_optim_sub import Study as witness_optim_sub_usecase
from climateeconomics.sos_processes.iam.witness.witness_optim_sub_process.usecase_witness_optim_sub import OPTIM_NAME, COUPLING_NAME, EXTRA_NAME
from sos_trades_core.execution_engine.func_manager.func_manager_disc import FunctionManagerDisc
from climateeconomics.core.design_variables_translation.witness_bspline.design_var_disc import Design_Var_Discipline
from energy_models.core.energy_study_manager import DEFAULT_TECHNO_DICT
from climateeconomics.core.tools.ClimateEconomicsStudyManager import ClimateEconomicsStudyManager
from energy_models.core.energy_process_builder import INVEST_DISCIPLINE_OPTIONS


OBJECTIVE = FunctionManagerDisc.OBJECTIVE
INEQ_CONSTRAINT = FunctionManagerDisc.INEQ_CONSTRAINT
EQ_CONSTRAINT = FunctionManagerDisc.EQ_CONSTRAINT
OBJECTIVE_LAGR = FunctionManagerDisc.OBJECTIVE_LAGR
FUNC_DF = FunctionManagerDisc.FUNC_DF
EXPORT_CSV = FunctionManagerDisc.EXPORT_CSV
WRITE_XVECT = Design_Var_Discipline.WRITE_XVECT


class Study(ClimateEconomicsStudyManager):

    def __init__(self, year_start=2020, year_end=2100, time_step=1, bspline=False, run_usecase=False, execution_engine=None,
                 invest_discipline=INVEST_DISCIPLINE_OPTIONS[1], techno_dict=DEFAULT_TECHNO_DICT):

        super().__init__(__file__, run_usecase=run_usecase, execution_engine=execution_engine)
        self.year_start = year_start
        self.year_end = year_end
        self.time_step = time_step
        self.optim_name = OPTIM_NAME
        self.coupling_name = COUPLING_NAME
        self.extra_name = EXTRA_NAME
        self.bspline = bspline
        self.invest_discipline = invest_discipline
        self.techno_dict = techno_dict

        self.witness_uc = witness_optim_sub_usecase(
            self.year_start, self.year_end, self.time_step,  bspline=self.bspline, execution_engine=execution_engine,
            invest_discipline=self.invest_discipline, techno_dict=techno_dict)
        self.sub_study_path_dict = self.witness_uc.sub_study_path_dict

    def setup_process(self):

        witness_optim_sub_usecase.setup_process(self)

    def setup_usecase(self):
        ns = self.study_name

        values_dict = {}

        self.witness_uc.study_name = f'{ns}.{self.optim_name}'
        self.coupling_name = self.witness_uc.coupling_name
        witness_uc_data = self.witness_uc.setup_usecase()
        for dict_data in witness_uc_data:
            values_dict.update(dict_data)

        # design space WITNESS
        dspace_df = self.witness_uc.dspace

        # df_xvect = pd.read_pickle('df_xvect.pkl')
        # df_xvect.columns = [df_xvect.columns[0]]+[col.split('.')[-1] for col in df_xvect.columns[1:]]
        # dspace_df_xvect=pd.DataFrame({'variable':df_xvect.columns, 'value':df_xvect.drop(0).values[0]})
        # dspace_df.update(dspace_df_xvect)

        dspace_size = self.witness_uc.dspace_size
        # optimization functions:
        optim_values_dict = {f'{ns}.epsilon0': 1,
                             f'{ns}.{self.optim_name}.design_space': dspace_df,
                             f'{ns}.{self.optim_name}.objective_name': FunctionManagerDisc.OBJECTIVE_LAGR,
                             f'{ns}.{self.optim_name}.eq_constraints': [],
                             f'{ns}.{self.optim_name}.ineq_constraints': [],

                             # optimization parameters:
                             f'{ns}.{self.optim_name}.max_iter': 500,
                             f'{ns}.warm_start': True,
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.warm_start': True,
                             # SLSQP, NLOPT_SLSQP
                             f'{ns}.{self.optim_name}.algo': "L-BFGS-B",
                             f'{ns}.{self.optim_name}.formulation': 'DisciplinaryOpt',
                             f'{ns}.{self.optim_name}.differentiation_method': 'user',
                             f'{ns}.{self.optim_name}.algo_options': {"ftol_rel": 3e-16,
                                                                      "normalize_design_space": False,
                                                                      "maxls": 2 * dspace_size,
                                                                      "maxcor": dspace_size,
                                                                      "pg_tol": 1.e-8,
                                                                      "max_iter": 500,
                                                                      "disp": 110},

                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.linear_solver_MDO_options': {'tol': 1.0e-10,
                                                                                                                   'max_iter': 10000},
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.linear_solver_MDA_options': {'tol': 1.0e-10,
                                                                                                                   'max_iter': 50000},
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.epsilon0': 1.0,
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.tolerance': 1.0e-10,

                             f'{ns}.{self.optim_name}.parallel_options': {"parallel": False,  # True
                                                                          "n_processes": 32,
                                                                          "use_threading": False,
                                                                          "wait_time_between_fork": 0},
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.sub_mda_class': 'GSorNewtonMDA',
                             f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.max_mda_iter': 50, }
# f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.DesignVariables.{WRITE_XVECT}':
# True}

        #print("Design space dimension is ", dspace_size)

        return [values_dict] + [optim_values_dict]


if '__main__' == __name__:
    uc_cls = Study(run_usecase=True)
    uc_cls.load_data()
    print(
        len(uc_cls.execution_engine.root_process.sos_disciplines[0].sos_disciplines[0].sos_disciplines))
    # df_xvect = pd.read_pickle('df_xvect.pkl')
    # df_xvect.columns = [
    # f'{uc_cls.study_name}.{uc_cls.optim_name}.{uc_cls.coupling_name}.DesignVariables' + col for col in df_xvect.columns]
    # dict_xvect = df_xvect.iloc[-1].to_dict()
    # dict_xvect[f'{uc_cls.study_name}.{uc_cls.optim_name}.eval_mode'] = True
    # uc_cls.load_data(from_input_dict=dict_xvect)
    # f'{ns}.{self.optim_name}.{self.witness_uc.coupling_name}.DesignVariables'
    # uc_cls.execution_engine.root_process.sos_disciplines[0].set_opt_scenario()
    # uc_cls.execution_engine.set_debug_mode()
    uc_cls.run()

#     uc_cls.execution_engine.root_process.sos_disciplines[0].coupling_structure.graph.export_reduced_graph(
#         "reduced.pdf")
#     uc_cls.execution_engine.root_process.sos_disciplines[0].coupling_structure.graph.export_initial_graph(
#         "initial.pdf")