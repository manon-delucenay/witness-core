'''
Copyright 2022 Airbus SAS
Modifications on 2023/04/06-2023/11/02 Copyright 2023 Capgemini

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
import logging
from typing import Union
from sostrades_core.execution_engine.sos_mdo_discipline import SoSMDODiscipline
from gemseo.mda.mda_chain import MDAChain
from sostrades_core.execution_engine.sos_mda_chain import SoSMDAChain
from sostrades_core.execution_engine.sos_mdo_scenario import SoSMDOScenario

'''
mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8
'''


class MDODisciplineWrappException(Exception):
    pass


class MDODisciplineWrapp(object):
    '''**MDODisciplineWrapp** is the interface to create MDODiscipline from SoSTrades wrappers, GEMSEO objects, etc.

    An instance of MDODisciplineWrapp is in one-to-one aggregation with an instance inheriting from MDODiscipline and
    might or might not have a SoSWrapp to supply the user-defined model run. All GEMSEO objects are instantiated during
    the prepare_execution phase.

    Attributes:
        name (string): name of the discipline/node
        wrapping_mode (string): mode of supply of model run by user ('SoSTrades'/'GEMSEO')
        mdo_discipline (MDODiscipline): aggregated GEMSEO object used for execution eventually with model run
        wrapper (SoSWrapp/???): wrapper instance used to supply the model run to the MDODiscipline (or None)
    '''

    def __init__(self, name: str, logger: logging.Logger, wrapper=None, wrapping_mode: str = 'SoSTrades'):
        '''
        Constructor.

        Arguments:
            name (string): name of the discipline/node
            wrapper (Class): class constructor of the user-defined wrapper (or None)
            wrapping_mode (string): mode of supply of model run by user ('SoSTrades'/'GEMSEO')
        '''
        self.logger = logger
        self.name = name
        self.wrapping_mode = wrapping_mode
        self.mdo_discipline: Union[SoSMDODiscipline, SoSMDOScenario, SoSMDAChain] = None
        if wrapper is not None:
            self.wrapper = wrapper(name, self.logger.getChild(wrapper.__name__))
        else:
            self.wrapper = None

    def get_input_data_names(self, filtered_inputs=False):
        """
        Return the names of the input variables.

        Arguments:
            filtered_inputs (bool): flag whether to filter the input names.

        Returns:
            The names of the input variables.
        """
        return self.mdo_discipline.get_input_data_names(filtered_inputs)

    def get_output_data_names(self, filtered_outputs=False):
        """Return the names of the output variables.

        Arguments:
            filtered_outputs (bool): flag whether to filter the output names.

        Returns:
            The names of the input variables.
        """
        return self.mdo_discipline.get_output_data_names(filtered_outputs)

    def setup_sos_disciplines(self):  # type: (...) -> None
        """
        Dynamic setup delegated to the wrapper using the proxy for i/o configuration.

        Arguments:
            proxy (ProxyDiscipline): corresponding proxy discipline
        """
        if self.wrapper is not None:
            self.wrapper.setup_sos_disciplines()

    def check_data_integrity(self):  # type: (...) -> None
        """
        check_data_integrity delegated to the wrapper using the proxy for i/o configuration.

        Arguments:
            proxy (ProxyDiscipline): corresponding proxy discipline
        """
        if self.wrapper is not None:
            self.wrapper.check_data_integrity()

    def create_gemseo_discipline(self, proxy=None, reduced_dm=None, cache_type=None, cache_file_path=None):
        """
        SoSMDODiscipline instanciation.

        Arguments:
            proxy (ProxyDiscipline): proxy discipline grammar initialisation
            input_data (dict): input values to update default values of the MDODiscipline with
            reduced_dm (Dict[Dict]): reduced data manager without values for i/o configuration
            cache_type (string): type of cache to be passed to the MDODiscipline
            cache_file_path (string): file path of the pickle file to dump/load the cache [???]
        """
        if self.wrapping_mode == 'SoSTrades':
            self.mdo_discipline = SoSMDODiscipline(full_name=proxy.get_disc_full_name(),
                                                   grammar_type=proxy.SOS_GRAMMAR_TYPE,
                                                   cache_type=cache_type,
                                                   cache_file_path=cache_file_path,
                                                   sos_wrapp=self.wrapper,
                                                   reduced_dm=reduced_dm,
                                                   logger=self.logger.getChild("SoSMDODiscipline")
                                                   )
            self._init_grammar_with_keys(proxy)
            self._set_wrapper_attributes(proxy, self.wrapper)
            self._update_all_default_values(proxy)
            self.mdo_discipline.linearization_mode = proxy.get_sosdisc_inputs(SoSMDODiscipline.LINEARIZATION_MODE)
            # self._set_discipline_attributes(proxy, self.mdo_discipline)

        elif self.wrapping_mode == 'GEMSEO':
            pass

    def _set_wrapper_attributes(self, proxy, wrapper):
        proxy.set_wrapper_attributes(wrapper)

    # def _set_discipline_attributes(self, proxy, discipline):
    #     proxy.set_discipline_attributes(discipline)

    def _init_grammar_with_keys(self, proxy):
        '''
        initialize GEMS grammar with names and type None

        Arguments:
            proxy (ProxyDiscipline): the proxy discipline to get input and output full names from
        '''
        input_names = proxy.get_input_data_names()
        grammar = self.mdo_discipline.input_grammar
        grammar.clear()
        grammar.initialize_from_base_dict(
            {input: None for input in input_names})

        output_names = proxy.get_output_data_names()
        grammar = self.mdo_discipline.output_grammar
        grammar.clear()
        grammar.initialize_from_base_dict(
            {output: None for output in output_names})

    def update_default_from_dict(self, input_dict, check_input=True):
        '''
        Store values from input_dict in default values of mdo_discipline (when keys are present in input grammar data
        names or input is not checked)

        Arguments:
            input_dict (dict): values to store
            check_input (bool): flag to specify if inputs are checked or not to exist in input grammar
        '''
        if input_dict is not None:
            to_update = [(key, value) for (key, value) in input_dict.items()
                         if not check_input or key in self.mdo_discipline.input_grammar.get_data_names()]
            self.mdo_discipline._default_inputs.update(to_update)

    def create_mda_chain(self, sub_mdo_disciplines, proxy=None, input_data=None,
                         reduced_dm=None):  # type: (...) -> None
        """
        MDAChain instantiation when owned by a ProxyCoupling.

        Arguments:
            sub_mdo_disciplines (List[MDODiscipline]): list of sub-MDODisciplines of the MDAChain
            proxy (ProxyDiscipline): proxy discipline for grammar initialisation
            input_data (dict): input data to update default values of the MDAChain with
        """
        if self.wrapping_mode == 'SoSTrades':
            mdo_discipline = SoSMDAChain(
                disciplines=sub_mdo_disciplines,
                reduced_dm=reduced_dm,
                name=proxy.get_disc_full_name(),
                grammar_type=proxy.SOS_GRAMMAR_TYPE,
                **proxy._get_numerical_inputs(),
                # authorize_self_coupled_disciplines=proxy.get_sosdisc_inputs(proxy.AUTHORIZE_SELF_COUPLED_DISCIPLINES),
                logger=self.logger.getChild("SoSMDAChain")
            )

            self.mdo_discipline = mdo_discipline

            self.__update_gemseo_grammar(proxy, mdo_discipline)

            # set linear solver options (todo after call to _get_numerical_inputs() )
            # TODO: check with IRT how to handle it
            mdo_discipline.linear_solver_MDA = proxy.linear_solver_MDA
            mdo_discipline.linear_solver_options_MDA = proxy.linear_solver_options_MDA
            mdo_discipline.linear_solver_tolerance_MDA = proxy.linear_solver_tolerance_MDA
            mdo_discipline.linear_solver_MDO = proxy.linear_solver_MDO
            mdo_discipline.linear_solver_options_MDO = proxy.linear_solver_options_MDO
            mdo_discipline.linear_solver_tolerance_MDO = proxy.linear_solver_tolerance_MDO
            mdo_discipline.linearization_mode = proxy.get_sosdisc_inputs(
                SoSMDODiscipline.LINEARIZATION_MODE)

            # # set other additional options (SoSTrades)
            # mdo_discipline.authorize_self_coupled_disciplines = proxy.get_sosdisc_inputs(
            #     'authorize_self_coupled_disciplines')

            #             self._init_grammar_with_keys(proxy)
            # self._update_all_default_values(input_data) # TODO: check why/if it is really needed
            proxy.status = self.mdo_discipline.status

        elif self.wrapping_mode == 'GEMSEO':
            pass

    def create_mdo_scenario(self, sub_mdo_disciplines, proxy=None,
                            reduced_dm=None):  # type: (...) -> None
        """
        SoSMDOScenario instantiation when owned by a ProxyOptim.

        Arguments:
            sub_mdo_disciplines (List[MDODiscipline]): list of sub-MDODisciplines of the MDAChain
            proxy (ProxyDiscipline): proxy discipline for grammar initialisation
            input_data (dict): input data to update default values of the MDAChain with
        """
        if self.wrapping_mode == 'SoSTrades':
            # Pass as arguments to __init__ parameters needed for MDOScenario
            # creation
            mdo_discipline = SoSMDOScenario(
                sub_mdo_disciplines, proxy.sos_name, proxy.formulation, proxy.objective_name, proxy.design_space,
                logger=self.logger.getChild("SoSMDOScenario"),
                grammar_type=proxy.SOS_GRAMMAR_TYPE, reduced_dm=reduced_dm)
            # Set parameters for SoSMDOScenario
            mdo_discipline.eval_mode = proxy.eval_mode
            mdo_discipline.maximize_objective = proxy.maximize_objective
            mdo_discipline.algo_name = proxy.algo_name
            mdo_discipline.algo_options = proxy.algo_options
            mdo_discipline.max_iter = proxy.max_iter
            mdo_discipline.eval_mode = proxy.eval_mode
            mdo_discipline.eval_jac = proxy.eval_jac
            mdo_discipline.dict_desactivated_elem = proxy.dict_desactivated_elem
            mdo_discipline.input_design_space = proxy.get_sosdisc_inputs('design_space')

            self.mdo_discipline = mdo_discipline

            self.__update_gemseo_grammar(proxy, mdo_discipline)
            proxy.status = self.mdo_discipline.status

        elif self.wrapping_mode == 'GEMSEO':
            pass

    def _update_all_default_values(self, proxy):
        '''Store all input grammar data names' values from input data in default values of mdo_discipline
        '''

        for key, value in proxy.get_data_in().items():
            if value['default'] is not None:
                full_key = proxy.get_var_full_name(key, proxy.get_data_in())
                self.mdo_discipline._default_inputs.update(
                    {full_key: value['default']})

    def __update_gemseo_grammar(self, proxy, mdachain):
        ''' 
        update GEMSEO grammar with sostrades 
        # NOTE: this introduces a gap between the MDAChain i/o grammar and those of the MDOChain, as attribute of MDAChain
        '''
        # - retrieve all the i/o of the ProxyCoupling that are not in the GEMSEO grammar of the MDAChain
        # (e.g., numerical inputs mainly)
        # TODO: [to discuss] ensure that/if all the SoSTrades added i/o ProxyCoupling are flagged as numerical, we can use this flag instead of performing set operations.
        #       -> need to check that outputs can be numerical (to cover the case of residuals for example, that is an output)
        soscoupling_inputs = set(proxy.get_input_data_names())
        mdachain_inputs = set(mdachain.get_input_data_names())
        missing_inputs = soscoupling_inputs - mdachain_inputs

        soscoupling_outputs = set(proxy.get_output_data_names())
        mdachain_outputs = set(mdachain.get_output_data_names())
        missing_outputs = soscoupling_outputs - mdachain_outputs

        # i/o grammars update with SoSTrades i/o
        for names, grammar in zip([missing_inputs, missing_outputs], [mdachain.input_grammar, mdachain.output_grammar]):
            # fake data dict with NoneType
            data_dict = dict.fromkeys(names, None)
            # This works since (for now) this method (for SimpleGrammar only)
            # does not clear the existing grammar of MDAChain
            grammar.initialize_from_base_dict(data_dict)

    def execute(self, input_data):
        """
        Discipline execution delegated to the GEMSEO objects.
            """

        return self.mdo_discipline.execute(input_data)
