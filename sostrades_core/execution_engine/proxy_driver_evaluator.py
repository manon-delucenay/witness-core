'''
Copyright 2022 Airbus SAS
Modifications on 2023/03/03-2023/11/02 Copyright 2023 Capgemini

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

'''
mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8
'''

import logging
from typing import Optional
import copy
import pandas as pd
from numpy import NaN
import numpy as np

from sostrades_core.execution_engine.sos_wrapp import SoSWrapp
from sostrades_core.execution_engine.proxy_discipline import ProxyDiscipline
from sostrades_core.execution_engine.proxy_coupling import ProxyCoupling
from sostrades_core.execution_engine.proxy_discipline_builder import ProxyDisciplineBuilder
from sostrades_core.execution_engine.mdo_discipline_driver_wrapp import MDODisciplineDriverWrapp
from sostrades_core.execution_engine.disciplines_wrappers.driver_evaluator_wrapper import DriverEvaluatorWrapper
from sostrades_core.execution_engine.disciplines_wrappers.sample_generator_wrapper import SampleGeneratorWrapper
from sostrades_core.tools.proc_builder.process_builder_parameter_type import ProcessBuilderParameterType
from gemseo.utils.compare_data_manager_tooling import dict_are_equal
from sostrades_core.tools.builder_info.builder_info_functions import get_ns_list_in_builder_list
from gemseo.utils.compare_data_manager_tooling import compare_dict


class ProxyDriverEvaluatorException(Exception):
    pass


class ProxyDriverEvaluator(ProxyDisciplineBuilder):
    '''
        SOSEval class which creates a sub process to evaluate
        with different methods (Gradient,FORM,Sensitivity Analysis, DOE, ...)

    1) Structure of Desc_in/Desc_out:
        |_ DESC_IN
            |_ INSTANCE_REFERENCE (structuring, dynamic : builder_mode == self.MULTI_INSTANCE)
                |_ REFERENCE_MODE (structuring, dynamic :instance_referance == TRUE) 
                |_ REFERENCE_SCENARIO_NAME (structuring, dynamic :instance_referance == TRUE) #TODO
            |_ EVAL_INPUTS (namespace: NS_EVAL, structuring, dynamic : builder_mode == self.MONO_INSTANCE)
            |_ EVAL_OUTPUTS (namespace: NS_EVAL, structuring, dynamic : builder_mode == self.MONO_INSTANCE)
            |_ GENERATED_SAMPLES ( structuring,dynamic: self.builder_tool == True)
            |_ SCENARIO_DF (structuring,dynamic: self.builder_tool == True)
            |_ SAMPLES_DF (namespace: NS_EVAL, dynamic: len(selected_inputs) > 0 and len(selected_outputs) > 0 )    
            |_ 'n_processes' (dynamic : builder_mode == self.MONO_INSTANCE)         
            |_ 'wait_time_between_fork' (dynamic : builder_mode == self.MONO_INSTANCE)

        |_ DESC_OUT
            |_ samples_inputs_df (namespace: NS_EVAL, dynamic: builder_mode == self.MONO_INSTANCE)
            |_ <var>_dict (internal namespace 'ns_doe', dynamic: len(selected_inputs) > 0 and len(selected_outputs) > 0
            and eval_outputs not empty, for <var> in eval_outputs)

    2) Description of DESC parameters:
        |_ DESC_IN
            |_ INSTANCE_REFERENCE 
                |_ REFERENCE_MODE 
                |_ REFERENCE_SCENARIO_NAME  #TODO
            |_ EVAL_INPUTS
            |_ EVAL_OUTPUTS
            |_ GENERATED_SAMPLES
            |_ SCENARIO_DF
            |_ SAMPLES_DF
            |_ 'n_processes' 
            |_ 'wait_time_between_fork'            
       |_ DESC_OUT
            |_ samples_inputs_df
            |_ <var observable name>_dict':     for each selected output observable doe result
                                                associated to sample and the selected observable

    '''

    # ontology information
    _ontology_data = {
        'label': 'Driver Evaluator',
        'type': 'Official',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': '',
        'version': '',
    }

    BUILDER_MODE = DriverEvaluatorWrapper.BUILDER_MODE
    MONO_INSTANCE = DriverEvaluatorWrapper.MONO_INSTANCE
    MULTI_INSTANCE = DriverEvaluatorWrapper.MULTI_INSTANCE
    REGULAR_BUILD = DriverEvaluatorWrapper.REGULAR_BUILD
    BUILDER_MODE_POSSIBLE_VALUES = DriverEvaluatorWrapper.BUILDER_MODE_POSSIBLE_VALUES
    SUB_PROCESS_INPUTS = DriverEvaluatorWrapper.SUB_PROCESS_INPUTS
    GATHER_DEFAULT_SUFFIX = DriverEvaluatorWrapper.GATHER_DEFAULT_SUFFIX

    INSTANCE_REFERENCE = 'instance_reference'
    LINKED_MODE = 'linked_mode'
    COPY_MODE = 'copy_mode'
    REFERENCE_MODE = 'reference_mode'
    REFERENCE_MODE_POSSIBLE_VALUES = [LINKED_MODE, COPY_MODE]
    REFERENCE_SCENARIO_NAME = 'ReferenceScenario'

    SCENARIO_DF = 'scenario_df'

    SELECTED_SCENARIO = 'selected_scenario'
    SCENARIO_NAME = 'scenario_name'
    # with SampleGenerator, whether to activate and build all the sampled
    MAX_SAMPLE_AUTO_BUILD_SCENARIOS = 1024
    # scenarios by default or not. Set to None to always build.

    SUBCOUPLING_NAME = 'subprocess'
    EVAL_INPUTS = 'eval_inputs'
    EVAL_OUTPUTS = 'eval_outputs'
    EVAL_INPUT_TYPE = ['float', 'array', 'int', 'string']

    GENERATED_SAMPLES = SampleGeneratorWrapper.GENERATED_SAMPLES

    USECASE_DATA = 'usecase_data'

    # shared namespace of the mono-instance evaluator for eventual couplings
    NS_EVAL = 'ns_eval'

    MULTIPLIER_PARTICULE = '__MULTIPLIER__'

    def __init__(self, sos_name, ee, cls_builder,
                 driver_wrapper_cls=None,
                 associated_namespaces=None,
                 map_name=None,
                 flatten_subprocess=False,
                 display_options=None,
                 ):
        """
        Constructor

        Arguments:
            sos_name (string): name of the discipline/node
            ee (ExecutionEngine): execution engine of the current process
            cls_builder (List[SoSBuilder]): list of the sub proxy builders
            driver_wrapper_cls (Class): class constructor of the driver wrapper (user-defined wrapper or SoSTrades wrapper or None)
            map_name (string): name of the map associated to the scatter builder in case of multi-instance build
            associated_namespaces(List[string]): list containing ns ids ['name__value'] for namespaces associated to builder
            logger (logging.Logger): Logger to use
        """
        super().__init__(sos_name, ee, driver_wrapper_cls, associated_namespaces=associated_namespaces)
        if cls_builder is not None:
            self.cls_builder = cls_builder
            self.sub_builder_namespaces = get_ns_list_in_builder_list(
                self.cls_builder)
        else:
            raise Exception(
                'The driver evaluator builder must have a cls_builder to work')

        self.builder_tool = None

        self.map_name = map_name
        self.flatten_subprocess = flatten_subprocess
        self.scenarios = []  # to keep track of subdisciplines in a flatten_subprocess case

        self.display_options = display_options

        self.old_builder_mode = None
        self.eval_process_builder = None
        self.eval_in_list = None
        self.eval_out_list = None
        self.selected_inputs = []
        self.selected_outputs = []
        self.eval_out_names = []
        self.eval_out_type = []
        self.eval_out_list_size = []

        self.old_samples_df, self.old_scenario_df = ({}, {})
        self.scatter_list_valid = True
        self.scatter_list_integrity_msg = ''

        self.previous_sub_process_usecase_name = 'Empty'
        self.previous_sub_process_usecase_data = {}
        # Possible values: 'No_SP_UC_Import', 'SP_UC_Import'
        self.sub_proc_import_usecase_status = 'No_SP_UC_Import'

        self.old_ref_dict = {}
        self.old_scenario_names = []
        self.save_editable_attr = True
        self.original_editability_dict = {}
        self.original_editable_dict_ref = {}
        self.original_editable_dict_non_ref = {}
        self.there_are_new_scenarios = False

        self.gather_names = None

    def _add_optional_shared_ns(self):
        """
        Add the shared namespace NS_EVAL should it not exist.
        """
        # do the same for the shared namespace for coupling with the DriverEvaluator
        # also used to store gathered variables in multi-instance
        if self.NS_EVAL not in self.ee.ns_manager.shared_ns_dict.keys():
            self.ee.ns_manager.add_ns(
                self.NS_EVAL, self.ee.ns_manager.compose_local_namespace_value(self))

    def _get_disc_shared_ns_value(self):
        """
        Get the namespace ns_eval used in the mono-instance case.
        """
        return self.ee.ns_manager.disc_ns_dict[self]['others_ns'][self.NS_EVAL].get_value()

    def get_desc_in_out(self, io_type):
        """
        get the desc_in or desc_out. if a wrapper exists get it from the wrapper, otherwise get it from the proxy class
        """
        # TODO : check if the following logic could be OK and implement it
        # according to what we want to do : DESC_IN of Proxy is updated by SoSWrapp if exists
        # thus no mixed calls to n-1 and n-2

        if self.mdo_discipline_wrapp.wrapper is not None:
            # ProxyDiscipline gets the DESC from the wrapper
            return ProxyDiscipline.get_desc_in_out(self, io_type)
        else:
            # ProxyDisciplineBuilder expects the DESC on the proxies e.g. Coupling
            # TODO: move to coupling ?
            return super().get_desc_in_out(io_type)

    def create_mdo_discipline_wrap(self, name, wrapper, wrapping_mode, logger:logging.Logger):
        """
        creation of mdo_discipline_wrapp by the proxy which in this case is a MDODisciplineDriverWrapp that will create
        a SoSMDODisciplineDriver at prepare_execution, i.e. a driver node that knows its subprocesses but manipulates
        them in a different way than a coupling.
        """
        self.mdo_discipline_wrapp = MDODisciplineDriverWrapp(name, logger.getChild("MDODisciplineDriverWrapp"), wrapper, wrapping_mode)

    def configure(self):
        """
        Configure the DriverEvaluator layer
        """
        # set the scenarios references, for flattened subprocess configuration
        if self.flatten_subprocess and self.builder_tool:
            self.scenarios = self.builder_tool.get_all_built_disciplines()
        else:
            self.scenarios = self.proxy_disciplines

        # configure al processes stored in children
        for disc in self.get_disciplines_to_configure():
            disc.configure()

        # configure current discipline DriverEvaluator
        # if self._data_in == {} or (self.get_disciplines_to_configure() == []
        # and len(self.proxy_disciplines) != 0) or len(self.cls_builder) == 0:
        if self._data_in == {} or self.subprocess_is_configured():
            # Call standard configure methods to set the process discipline
            # tree
            super().configure()
            self.configure_driver()

        if self.subprocess_is_configured():
            self.update_data_io_with_subprocess_io()
            self.set_children_numerical_inputs()

    def update_data_io_with_subprocess_io(self):
        """
        Update the DriverEvaluator _data_in and _data_out with subprocess i/o so that grammar of the driver can be
        exploited for couplings etc.
        """
        self._restart_data_io_to_disc_io()
        for proxy_disc in self.proxy_disciplines:
            # if not isinstance(proxy_disc, ProxyDisciplineGather):
            subprocess_data_in = proxy_disc.get_data_io_with_full_name(
                self.IO_TYPE_IN, as_namespaced_tuple=True)
            subprocess_data_out = proxy_disc.get_data_io_with_full_name(
                self.IO_TYPE_OUT, as_namespaced_tuple=True)
            self._update_data_io(subprocess_data_in, self.IO_TYPE_IN)
            self._update_data_io(subprocess_data_out, self.IO_TYPE_OUT)

    def configure_driver(self):
        """
        To be overload by drivers with specific configuration actions
        """
        # Extract variables for eval analysis in mono instance mode
        disc_in = self.get_data_in()
        if self.BUILDER_MODE in disc_in:
            if self.get_sosdisc_inputs(self.BUILDER_MODE) == self.MONO_INSTANCE \
                    and self.EVAL_INPUTS in disc_in and len(self.proxy_disciplines) > 0:
                # CHECK USECASE IMPORT AND IMPORT IT IF NEEDED
                # Manage usecase import
                ref_discipline_full_name = f'{self.ee.study_name}.Eval'
                self.manage_import_inputs_from_sub_process(
                    ref_discipline_full_name)
                # SET EVAL POSSIBLE VALUES
                self.set_eval_possible_values()
            elif self.get_sosdisc_inputs(self.BUILDER_MODE) == self.MULTI_INSTANCE and self.SCENARIO_DF in disc_in:
                self.configure_tool()
                self.configure_subprocesses_with_driver_input()
                self.set_eval_possible_values(io_type_in=False, strip_first_ns=True)

    def setup_sos_disciplines(self):
        """
        Dynamic inputs and outputs of the DriverEvaluator
        """
        if self.BUILDER_MODE in self.get_data_in():
            builder_mode = self.get_sosdisc_inputs(self.BUILDER_MODE)
            disc_in = self.get_data_in()
            if builder_mode == self.MULTI_INSTANCE:
                self.build_multi_instance_inst_desc_io()
                if self.GENERATED_SAMPLES in disc_in:
                    generated_samples = self.get_sosdisc_inputs(
                        self.GENERATED_SAMPLES)
                    generated_samples_dict = {
                        self.GENERATED_SAMPLES: generated_samples}
                    scenario_df = self.get_sosdisc_inputs(self.SCENARIO_DF)
                    # checking whether generated_samples has changed
                    # NB also doing nothing with an empty dataframe, which means sample needs to be regenerated to renew
                    # scenario_df on 2nd config. The reason of this choice is that using an optional generated_samples
                    # gives problems with structuring variables checks leading
                    # to incomplete configuration sometimes
                    if not (generated_samples.empty and not self.old_samples_df) \
                            and not dict_are_equal(generated_samples_dict, self.old_samples_df):
                        # checking whether the dataframes are already coherent in which case the changes come probably
                        # from a load and there is no need to crush the truth
                        # values
                        if not generated_samples.equals(
                                scenario_df.drop([self.SELECTED_SCENARIO, self.SCENARIO_NAME], axis=1)):
                            # TODO: could overload struct. var. check to spare this deepcopy (only if generated_samples
                            #  remains as a DriverEvaluator input, othrwise another sample change check logic is needed)
                            self.old_samples_df = copy.deepcopy(
                                generated_samples_dict)
                            # we crush old scenario_df and propose a df with
                            # all scenarios imposed by new sample, all
                            # de-activated
                            scenario_df = pd.DataFrame(
                                columns=[self.SELECTED_SCENARIO, self.SCENARIO_NAME])
                            scenario_df = pd.concat(
                                [scenario_df, generated_samples], axis=1)
                            n_scenarios = len(scenario_df.index)
                            # check whether the number of generated scenarios
                            # is not too high to auto-activate them
                            if self.MAX_SAMPLE_AUTO_BUILD_SCENARIOS is None or n_scenarios <= self.MAX_SAMPLE_AUTO_BUILD_SCENARIOS:
                                scenario_df[self.SELECTED_SCENARIO] = True
                            else:
                                self.logger.warning(
                                    f'Sampled over {self.MAX_SAMPLE_AUTO_BUILD_SCENARIOS} scenarios, please select which to build. ')
                                scenario_df[self.SELECTED_SCENARIO] = False
                            scenario_name = scenario_df[self.SCENARIO_NAME]
                            for i in scenario_name.index.tolist():
                                scenario_name.iloc[i] = 'scenario_' + \
                                                        str(i + 1)
                            self.logger.info(
                                'Generated sample has changed, updating scenarios to select.')
                            self.dm.set_data(self.get_var_full_name(self.SCENARIO_DF, disc_in),
                                             'value', scenario_df, check_value=False)

            elif builder_mode == self.MONO_INSTANCE:
                dynamic_inputs = {self.EVAL_INPUTS: {self.TYPE: 'dataframe',
                                                  self.DATAFRAME_DESCRIPTOR: {'selected_input': ('bool', None, True),
                                                                              'full_name': ('string', None, False)},
                                                  self.DATAFRAME_EDITION_LOCKED: False,
                                                  self.STRUCTURING: True,
                                                  self.VISIBILITY: self.SHARED_VISIBILITY,
                                                  self.NAMESPACE: self.NS_EVAL},
                                  self.EVAL_OUTPUTS: {self.TYPE: 'dataframe',
                                                   self.DATAFRAME_DESCRIPTOR: {'selected_output': ('bool', None, True),
                                                                               'full_name': ('string', None, False),
                                                                               'output_name': ('multiple', None, True)},
                                                   self.DATAFRAME_EDITION_LOCKED: False,
                                                   self.STRUCTURING: True,
                                                   self.VISIBILITY: self.SHARED_VISIBILITY,
                                                   self.NAMESPACE: self.NS_EVAL},
                                  'n_processes': {self.TYPE: 'int', self.NUMERICAL: True, self.DEFAULT: 1},
                                  'wait_time_between_fork': {self.TYPE: 'float', self.NUMERICAL: True,
                                                             self.DEFAULT: 0.0}
                                  }

                dynamic_outputs = {
                    'samples_inputs_df': {self.TYPE: 'dataframe', 'unit': None, self.VISIBILITY: self.SHARED_VISIBILITY,
                                          self.NAMESPACE: self.NS_EVAL}
                }

                selected_inputs_has_changed = False
                if self.EVAL_INPUTS in disc_in:
                    # if len(disc_in) != 0:

                    eval_outputs = self.get_sosdisc_inputs(self.EVAL_OUTPUTS)
                    eval_inputs = self.get_sosdisc_inputs(self.EVAL_INPUTS)

                    # we fetch the inputs and outputs selected by the user
                    selected_outputs = eval_outputs[eval_outputs['selected_output']
                                                    == True]['full_name']
                    selected_inputs = eval_inputs[eval_inputs['selected_input']
                                                  == True]['full_name']
                    # FIXME: correct the testcases for data integrity
                    if 'output_name' in eval_outputs.columns:
                        eval_out_names = eval_outputs[eval_outputs['selected_output']
                                                        == True]['output_name'].tolist()
                    else:
                        eval_out_names = [None for _ in selected_outputs]
                    if set(selected_inputs.tolist()) != set(self.selected_inputs):
                        selected_inputs_has_changed = True
                        self.selected_inputs = selected_inputs.tolist()
                    self.selected_outputs = selected_outputs.tolist()

                    if len(selected_inputs) > 0 and len(selected_outputs) > 0:
                        # TODO: OK that it blocks config. with empty input ? also, might want an eval without outputs ?
                        # we set the lists which will be used by the evaluation function of sosEval
                        self.set_eval_in_out_lists(
                            self.selected_inputs, self.selected_outputs)

                        # setting dynamic outputs. One output of type dict per selected output
                        self.eval_out_names = []
                        for out_var, out_name in zip(self.selected_outputs, eval_out_names):
                            _out_name = out_name or f'{out_var}{self.GATHER_DEFAULT_SUFFIX}'
                            self.eval_out_names.append(_out_name)
                            dynamic_outputs.update(
                                {_out_name: {self.TYPE: 'dict',
                                             self.VISIBILITY: 'Shared',
                                             self.NAMESPACE: self.NS_EVAL}})
                        dynamic_inputs.update(self._get_dynamic_inputs_doe(
                            disc_in, selected_inputs_has_changed))
                        dynamic_outputs.update({'samples_outputs_df': {self.TYPE: 'dataframe',
                                                                       self.VISIBILITY: 'Shared',
                                                                       self.NAMESPACE: self.NS_EVAL}})
                self.add_inputs(dynamic_inputs)
                self.add_outputs(dynamic_outputs)
            elif builder_mode == self.REGULAR_BUILD:
                pass  # regular build requires no specific dynamic inputs
            elif builder_mode is None:
                pass
            else:
                raise ValueError(
                    f'Wrong builder mode input in {self.sos_name}')

        # after managing the different builds inputs, we do the setup_sos_disciplines of the wrapper in case it is
        # overload, e.g. in the case of a custom driver_wrapper_cls (with DriverEvaluatorWrapper this does nothing)
        # super().setup_sos_disciplines()

    def prepare_build(self):
        """
        Get the actual drivers of the subprocesses of the DriverEvaluator.
        """
        # NB: custom driver wrapper not implemented
        builder_list = []
        if self.BUILDER_MODE in self.get_data_in():
            builder_mode = self.get_sosdisc_inputs(self.BUILDER_MODE)
            builder_mode_has_changed = builder_mode != self.old_builder_mode
            if builder_mode_has_changed:
                self.clean_children()
                self.clean_sub_builders()
                if self.old_builder_mode == self.MONO_INSTANCE:
                    self.eval_process_builder = None
                elif self.old_builder_mode == self.MULTI_INSTANCE:
                    self.builder_tool = None
                self.old_builder_mode = copy.copy(builder_mode)
            if builder_mode == self.MULTI_INSTANCE:
                builder_list = self.prepare_multi_instance_build()
            elif builder_mode == self.MONO_INSTANCE:
                builder_list = self.prepare_mono_instance_build()
            elif builder_mode == self.REGULAR_BUILD:
                builder_list = super().prepare_build()
            elif builder_mode is None:
                pass
            else:
                raise ValueError(
                    f'Wrong builder mode input in {self.sos_name}')
        return builder_list

    def prepare_execution(self):
        """
        Preparation of the GEMSEO process, including GEMSEO objects instantiation
        """
        # prepare_execution of proxy_disciplines as in coupling
        for disc in self.scenarios:
            disc.prepare_execution()
        # TODO : cache mgmt of children necessary ? here or in  SoSMDODisciplineDriver ?
        super().prepare_execution()
        self.reset_subdisciplines_of_wrapper()

    def reset_subdisciplines_of_wrapper(self):
        self.mdo_discipline_wrapp.reset_subdisciplines(self)

    def set_wrapper_attributes(self, wrapper):
        """
        set the attribute ".attributes" of wrapper which is used to provide the wrapper with information that is
        figured out at configuration time but needed at runtime. The DriverEvaluator in particular needs to provide
        its wrapper with a reference to the subprocess GEMSEO objets so they can be manipulated at runtime.
        """
        # io full name maps set by ProxyDiscipline
        super().set_wrapper_attributes(wrapper)

        # driverevaluator subprocess
        wrapper.attributes.update({'sub_mdo_disciplines': [
            proxy.mdo_discipline_wrapp.mdo_discipline for proxy in self.proxy_disciplines
            if proxy.mdo_discipline_wrapp is not None]})  # discs and couplings but not scatters

        if self.BUILDER_MODE in self.get_data_in():
            builder_mode = self.get_sosdisc_inputs(self.BUILDER_MODE)
            eval_attributes = {}
            if builder_mode == self.MONO_INSTANCE and self.eval_in_list is not None:
                # specific to mono-instance
                eval_attributes = {'eval_in_list': self.eval_in_list,
                                   'eval_out_list': self.eval_out_list,
                                   'eval_out_names': self.eval_out_names,
                                   'reference_scenario': self.get_x0(),
                                   'activated_elems_dspace_df': [[True, True]
                                                                 if self.ee.dm.get_data(var,
                                                                                        self.TYPE) == 'array' else [
                                       True]
                                                                 for var in self.eval_in_list],
                                   # NB: this works with an array of dimensions >2 even though it looks incoherent
                                   'driver_name': self.get_disc_full_name(),
                                   'reduced_dm': self.ee.dm.reduced_dm,  # for conversions
                                   'selected_inputs': self.selected_inputs,
                                   'selected_outputs': self.selected_outputs,
                                   }
            elif builder_mode == self.MULTI_INSTANCE:
                # for the gatherlike capabilities
                eval_attributes = {'gather_names': self.gather_names,
                                   'gather_out_keys': self.gather_out_keys,
                                   }
            wrapper.attributes.update(eval_attributes)

    def is_configured(self):
        """
        Return False if discipline is not configured or structuring variables have changed or children are not all configured
        """
        disc_in = self.get_data_in()
        if self.BUILDER_MODE in disc_in:
            if self.get_sosdisc_inputs(self.BUILDER_MODE) == self.MULTI_INSTANCE:
                if self.INSTANCE_REFERENCE in disc_in and self.get_sosdisc_inputs(self.INSTANCE_REFERENCE):
                    if self.SCENARIO_DF in disc_in:
                        config_status = super().is_configured() and self.subprocess_is_configured()
                        config_status = config_status and (
                            not self.check_if_there_are_reference_variables_changes())
                        config_status = config_status and self.sub_proc_import_usecase_status == 'No_SP_UC_Import'
                        return config_status
            elif self.get_sosdisc_inputs(self.BUILDER_MODE) == self.MONO_INSTANCE:
                config_status = super().is_configured() and self.subprocess_is_configured()
                # The next condition is not needed (and not working)
                # config_status = config_status and self.sub_proc_import_usecase_status == 'No_SP_UC_Import'
                return config_status

        return super().is_configured() and self.subprocess_is_configured()

    def subprocess_is_configured(self):
        """
        Return True if the subprocess is configured or the builder is empty.
        """
        # Explanation:
        # 1. self._data_in == {} : if the discipline as no input key it should have and so need to be configured
        # 2. Added condition compared to SoSDiscipline(as sub_discipline or associated sub_process builder)
        # 2.1 (self.get_disciplines_to_configure() == [] and len(self.proxy_disciplines) != 0) : sub_discipline(s) exist(s) but all configured
        # 2.2 len(self.cls_builder) == 0 No yet provided builder but we however need to configure (as in 2.1 when we have sub_disciplines which no need to be configured)
        # Remark1: condition "(   and len(self.proxy_disciplines) != 0) or len(self.cls_builder) == 0" added for proc build
        # Remark2: /!\ REMOVED the len(self.proxy_disciplines) == 0 condition
        # to accommodate the DriverEvaluator that holds te build until inputs
        # are available
        return self.get_disciplines_to_configure() == []  # or len(self.cls_builder) == 0

    def get_disciplines_to_configure(self):
        return self._get_disciplines_to_configure(self.scenarios)

    def check_data_integrity(self):
        # checking for duplicates
        disc_in = self.get_data_in()
        if self.SCENARIO_DF in disc_in and not self.scatter_list_valid:
            self.dm.set_data(
                self.get_var_full_name(self.SCENARIO_DF, disc_in),
                self.CHECK_INTEGRITY_MSG, self.scatter_list_integrity_msg)

    def fill_possible_values(self, disc, io_type_in=True, io_type_out=True):
        '''
            Fill possible values lists for eval inputs and outputs
            an input variable must be a float coming from a data_in of a discipline in all the process
            and not a default variable
            an output variable must be any data from a data_out discipline
        '''
        poss_in_values_full = set()
        poss_out_values_full = set()
        if io_type_in: # TODO: edit this code if adding multi-instance eval_inputs in order to take structuring vars
            disc_in = disc.get_data_in()
            for data_in_key in disc_in.keys():
                is_input_type = disc_in[data_in_key][self.TYPE] in self.EVAL_INPUT_TYPE
                is_structuring = disc_in[data_in_key].get(
                    self.STRUCTURING, False)
                in_coupling_numerical = data_in_key in list(
                    ProxyCoupling.DESC_IN.keys())
                full_id = disc.get_var_full_name(
                    data_in_key, disc_in)
                is_in_type = self.dm.data_dict[self.dm.data_id_map[full_id]
                             ]['io_type'] == 'in'
                # is_input_multiplier_type = disc_in[data_in_key][self.TYPE] in self.INPUT_MULTIPLIER_TYPE
                is_editable = disc_in[data_in_key]['editable']
                is_None = disc_in[data_in_key]['value'] is None
                is_a_multiplier = self.MULTIPLIER_PARTICULE in data_in_key
                if is_in_type and not in_coupling_numerical and not is_structuring and is_editable:
                    # Caution ! This won't work for variables with points in name
                    # as for ac_model
                    # we remove the study name from the variable full  name for a
                    # sake of simplicity
                    if is_input_type and not is_a_multiplier:
                        poss_in_values_full.add(
                            full_id.split(f'{self.get_disc_full_name()}.', 1)[1])
                        # poss_in_values_full.append(full_id)

                    # if is_input_multiplier_type and not is_None:
                    #     poss_in_values_list = self.set_multipliers_values(
                    #         disc, full_id, data_in_key)
                    #     for val in poss_in_values_list:
                    #         poss_in_values_full.append(val)

        if io_type_out:
            disc_out = disc.get_data_out()
            for data_out_key in disc_out.keys():
                # Caution ! This won't work for variables with points in name
                # as for ac_model
                in_coupling_numerical = data_out_key in list(
                    ProxyCoupling.DESC_IN.keys()) or data_out_key == 'residuals_history'
                full_id = disc.get_var_full_name(
                    data_out_key, disc_out)
                if not in_coupling_numerical:
                    # we anonymize wrt. driver evaluator node namespace
                    poss_out_values_full.add(
                        full_id.split(f'{self.get_disc_full_name()}.', 1)[1])
                    # poss_out_values_full.append(full_id)
        return poss_in_values_full, poss_out_values_full

    def find_possible_values(
            self, disc, possible_in_values, possible_out_values,
            io_type_in=True, io_type_out=True):
        '''
            Run through all disciplines and sublevels
            to find possible values for eval_inputs and eval_outputs
        '''
        # TODO: does this involve avoidable, recursive back and forths during  configuration ? (<-> config. graph)
        if len(disc.proxy_disciplines) != 0:
            for sub_disc in disc.proxy_disciplines:
                sub_in_values, sub_out_values = self.fill_possible_values(
                    sub_disc, io_type_in=io_type_in, io_type_out=io_type_out)
                possible_in_values.update(sub_in_values)
                possible_out_values.update(sub_out_values)
                self.find_possible_values(
                    sub_disc, possible_in_values, possible_out_values,
                    io_type_in=io_type_in, io_type_out=io_type_out)

        return possible_in_values, possible_out_values

    def check_eval_io(self, given_list, default_list, is_eval_input):
        """
        Set the evaluation variable list (in and out) present in the DM
        which fits with the eval_in_base_list filled in the usecase or by the user
        """

        for given_io in given_list:
            if given_io not in default_list and not self.MULTIPLIER_PARTICULE in given_io:
                if is_eval_input:
                    error_msg = f'The input {given_io} in eval_inputs is not among possible values. Check if it is an ' \
                                f'input of the subprocess with the correct full name (without study name at the ' \
                                f'beginning) and within allowed types (int, array, float). Dynamic inputs might  not ' \
                                f'be created. should be in {default_list} '

                else:
                    error_msg = f'The output {given_io} in eval_outputs is not among possible values. Check if it is an ' \
                                f'output of the subprocess with the correct full name (without study name at the ' \
                                f'beginning). Dynamic inputs might  not be created. should be in {default_list}'

                self.logger.warning(error_msg)

    def clean_sub_builders(self):
        '''
        Clean sub_builders as they were at initialization especially for their associated namespaces
        '''
        for builder in self.cls_builder:
            # delete all associated namespaces
            builder.delete_all_associated_namespaces()
            # set back all associated namespaces that was at the init of the
            # evaluator
            builder.add_namespace_list_in_associated_namespaces(
                self.associated_namespaces)

    def manage_import_inputs_from_sub_process(self, ref_discipline_full_name):
        """
        """
        # Set sub_proc_import_usecase_status
        with_modal = True
        self.set_sub_process_usecase_status_from_user_inputs(with_modal)

        disc_in = self.get_data_in()

        # Treat the case of SP_UC_Import
        if self.sub_proc_import_usecase_status == 'SP_UC_Import':
            # Get the anonymized dict
            if with_modal:  # TODO (when use of Modal)
                anonymize_input_dict_from_usecase = self.get_sosdisc_inputs(
                    self.SUB_PROCESS_INPUTS)[ProcessBuilderParameterType.USECASE_DATA]
            else:
                # (without use of Modal)
                anonymize_input_dict_from_usecase = self.get_sosdisc_inputs(
                    self.USECASE_DATA)

            # LOAD REFERENCE of MULTI-INSTANCE MODE WITH USECASE DATA
            if self.INSTANCE_REFERENCE in disc_in:
                # method = 'set_values'
                self.update_reference_from_anonymised_dict(
                    anonymize_input_dict_from_usecase, ref_discipline_full_name, with_modal)

            elif self.BUILDER_MODE in disc_in:
                builder_mode = self.get_sosdisc_inputs(self.BUILDER_MODE)
                if builder_mode == self.MONO_INSTANCE:
                    # LOAD REFERENCE of MONO-INSTANCE MODE WITH USECASE DATA
                    # method = 'load_study'
                    self.update_reference_from_anonymised_dict(
                        anonymize_input_dict_from_usecase, ref_discipline_full_name, with_modal)
            else:
                # We are in multi instance qithout reference
                # LOAD ALL SCENARIOS of MULTI-INSTANCE MODE WITH USECASE DATA
                # (Not needed as already covered)
                pass

    def update_reference_from_anonymised_dict(self, anonymize_input_dict_from_usecase, ref_discipline_full_name,
                                              with_modal):
        """
        """
        # 1. Put anonymized dict in context (unanonymize) of the reference
        # First identify the reference scenario
        input_dict_from_usecase = self.put_anonymized_input_dict_in_sub_process_context(
            anonymize_input_dict_from_usecase, ref_discipline_full_name)
        # print(input_dict_from_usecase)
        # self.ee.display_treeview_nodes(True)
        # 2. load data in dm (# Push the data to the reference
        # instance)

        # ======================================================================
        # if method == 'load_study':  # We sometimes in multi instance get an infinite loop and never do the last in the sequence
        #     self.ee.load_study_from_input_dict(
        #         input_dict_from_usecase)
        # elif method =='set_values':  # This is what was done before the bellow correction. It doesn't work with dynamic subproc or if a data kay is not yet in the dm
        #     self.ee.dm.set_values_from_dict(
        #         input_dict_from_usecase)
        # self.ee.dm.set_values_from_dict(filtered_import_dict)
        # ======================================================================

        # Here is a NEW method : with filtering. With this method something is
        # added in is_configured function
        filtered_import_dict = {}
        for key in input_dict_from_usecase:
            if self.ee.dm.check_data_in_dm(key):
                filtered_import_dict[key] = input_dict_from_usecase[key]

        self.ee.dm.set_values_from_dict(filtered_import_dict)

        are_all_data_set = len(filtered_import_dict.keys()) == len(
            input_dict_from_usecase.keys())

        # Remark 1: This condition will be a problem if the users is putting a bad key of variable in its anonymized dict
        # It may be ok if the anonymized dict comes from a uses case ? --> so
        # having wrong keys may be not needed to be treated

        # Remark 2: however with this filtering we should verify that we will always have all the variable pushed at the end
        # (we should not miss data that were provided in the anonymized dict) : but this will be the case all valid keys
        # will be set in the dm if it is a appropriate key (based on the
        # dynamic configuration)

        # Remark 3: What could be done is: if we reach the 100 iterations limit because are_all_data_set is still not True
        # then provide a warning with the list of variables keys that makes are_all_data_set still be False

        # Remark 4: (Better improvement)  next Provide another mechanism at eev4 level in which you always can push data
        # in dm provide check and warning when you reach the end of the configuration.

        if are_all_data_set:
            # TODO Bug if 100 config reached ( a bad key in anonymised dict) .
            # In this case are_all_data_set always False and we do not reset all parameters as it should !
            # 3. Update parameters
            #     Set the status to 'No_SP_UC_Import'
            self.sub_proc_import_usecase_status = 'No_SP_UC_Import'
            if with_modal:  # TODO (when use of Modal)
                # Empty the anonymized dict in (when use of Modal)
                sub_process_inputs_dict = self.get_sosdisc_inputs(
                    self.SUB_PROCESS_INPUTS)
                sub_process_inputs_dict[ProcessBuilderParameterType.USECASE_DATA] = {
                }
                # Consequently update the previous_sub_process_usecase_data
                sub_process_usecase_name = sub_process_inputs_dict[
                    ProcessBuilderParameterType.USECASE_INFO][ProcessBuilderParameterType.USECASE_NAME]
                sub_process_usecase_data = sub_process_inputs_dict[
                    ProcessBuilderParameterType.USECASE_DATA]
                self.previous_sub_process_usecase_name = sub_process_usecase_name
                self.previous_sub_process_usecase_data = sub_process_usecase_data
                self.previous_sub_process_usecase_data = {}
            else:
                # Consequently update the previous_sub_process_usecase_data
                sub_process_usecase_data = self.get_sosdisc_inputs(
                    self.USECASE_DATA)
                self.previous_sub_process_usecase_data = sub_process_usecase_data

    def set_sub_process_usecase_status_from_user_inputs(self, with_modal):
        """
            State subprocess usecase import status
            The uscase is defined by its name and its anonimized dict
            Function needed in manage_import_inputs_from_sub_process()
        """
        disc_in = self.get_data_in()

        if with_modal:
            if self.SUB_PROCESS_INPUTS in disc_in:  # and self.sub_proc_build_status != 'Empty_SP'
                sub_process_inputs_dict = self.get_sosdisc_inputs(
                    self.SUB_PROCESS_INPUTS)
                sub_process_usecase_name = sub_process_inputs_dict[
                    ProcessBuilderParameterType.USECASE_INFO][ProcessBuilderParameterType.USECASE_NAME]
                sub_process_usecase_data = sub_process_inputs_dict[
                    ProcessBuilderParameterType.USECASE_DATA]
                if self.previous_sub_process_usecase_name != sub_process_usecase_name or self.previous_sub_process_usecase_data != sub_process_usecase_data:
                    # not not sub_process_usecase_data True means it is not an
                    # empty dictionary
                    if sub_process_usecase_name != 'Empty' and not not sub_process_usecase_data:
                        self.sub_proc_import_usecase_status = 'SP_UC_Import'
                else:
                    self.sub_proc_import_usecase_status = 'No_SP_UC_Import'
            else:
                self.sub_proc_import_usecase_status = 'No_SP_UC_Import'
        else:
            if self.USECASE_DATA in disc_in:
                sub_process_usecase_data = self.get_sosdisc_inputs(
                    self.USECASE_DATA)
                if self.previous_sub_process_usecase_data != sub_process_usecase_data:
                    # not not sub_process_usecase_data True means it is not an
                    # empty dictionary
                    if not not sub_process_usecase_data:
                        self.sub_proc_import_usecase_status = 'SP_UC_Import'
                else:
                    self.sub_proc_import_usecase_status = 'No_SP_UC_Import'
            else:
                self.sub_proc_import_usecase_status = 'No_SP_UC_Import'

    def put_anonymized_input_dict_in_sub_process_context(self, anonymize_input_dict_from_usecase,
                                                         ref_discipline_full_name):
        """
            Put_anonymized_input_dict in sub_process context
            Function needed in manage_import_inputs_from_sub_process()
        """
        # Get unanonymized dict (i.e. dict of subprocess in driver context)
        # from anonymized dict and context
        # Following treatment of substitution of the new_study_placeholder of value self.ref_discipline_full_name
        # may not to be done for all variables (see vsMS with ns_to_update that
        # has not all the ns keys)

        input_dict_from_usecase = {}
        new_study_placeholder = ref_discipline_full_name
        for key_to_unanonymize, value in anonymize_input_dict_from_usecase.items():
            converted_key = key_to_unanonymize.replace(
                self.ee.STUDY_PLACEHOLDER_WITHOUT_DOT, new_study_placeholder)
            # see def __unanonymize_key  in execution_engine
            uc_d = {converted_key: value}
            input_dict_from_usecase.update(uc_d)
        return input_dict_from_usecase

    # WIP on class pre-refactoring (identifying mono-instance and multi-instance methods)

    #######################################
    #######################################
    ##### MULTI-INSTANCE MODE METHODS #####
    #######################################
    #######################################

    def prepare_multi_instance_build(self):
        """
        Call the tool to build the subprocesses in multi-instance builder mode.
        """
        self.build_tool()
        # Tool is building disciplines for the driver on behalf of the driver name
        # no further disciplines needed to be builded by the evaluator
        return []

    def build_multi_instance_inst_desc_io(self):
        '''
        Complete inst_desc_in with scenario_df
        '''
        dynamic_inputs = {
            self.SCENARIO_DF: {
                self.TYPE: 'dataframe',
                self.DEFAULT: pd.DataFrame(columns=[self.SELECTED_SCENARIO, self.SCENARIO_NAME]),
                self.DATAFRAME_DESCRIPTOR: {self.SELECTED_SCENARIO: ('bool', None, True),
                                            self.SCENARIO_NAME: ('string', None, True)},
                self.DYNAMIC_DATAFRAME_COLUMNS: True,
                self.DATAFRAME_EDITION_LOCKED: False,
                self.EDITABLE: True,
                self.STRUCTURING: True
            },  # TODO: manage variable columns for (non-very-simple) multiscenario cases
            self.EVAL_OUTPUTS: {
                self.TYPE: 'dataframe',
                self.DEFAULT: pd.DataFrame(columns=['selected_output', 'full_name', 'output_name']),
                self.DATAFRAME_DESCRIPTOR: {'selected_output': ('bool', None, True),
                                            'full_name': ('string', None, False),
                                            'output_name': ('multiple', None, True)
                                            },
                self.DATAFRAME_EDITION_LOCKED: False,
                self.STRUCTURING: True,
                # TODO: run-time coupling is not possible but might want variable in NS_EVAL for config-time coupling ?
                # self.VISIBILITY: self.SHARED_VISIBILITY,
                # self.NAMESPACE: self.NS_EVAL
            },
            self.INSTANCE_REFERENCE: {
                self.TYPE: 'bool',
                self.DEFAULT: False,
                self.POSSIBLE_VALUES: [True, False],
                self.STRUCTURING: True
            }
        }

        disc_in = self.get_data_in()
        if self.INSTANCE_REFERENCE in disc_in:
            instance_reference = self.get_sosdisc_inputs(
                self.INSTANCE_REFERENCE)
            if instance_reference:
                dynamic_inputs.update({self.REFERENCE_MODE:
                                           {self.TYPE: 'string',
                                            # SoSWrapp.DEFAULT: self.LINKED_MODE,
                                            self.POSSIBLE_VALUES: self.REFERENCE_MODE_POSSIBLE_VALUES,
                                            self.STRUCTURING: True}})

        dynamic_inputs.update({self.GENERATED_SAMPLES: {self.TYPE: 'dataframe',
                                                        self.DATAFRAME_DESCRIPTOR: {
                                                            self.SELECTED_SCENARIO: ('string', None, False),
                                                            self.SCENARIO_NAME: ('string', None, False)},
                                                        self.DYNAMIC_DATAFRAME_COLUMNS: True,
                                                        self.DATAFRAME_EDITION_LOCKED: True,
                                                        self.STRUCTURING: True,
                                                        self.UNIT: None,
                                                        # self.VISIBILITY: SoSWrapp.SHARED_VISIBILITY,
                                                        # self.NAMESPACE: 'ns_sampling',
                                                        self.DEFAULT: pd.DataFrame(),
                                                        # self.OPTIONAL:
                                                        # True,
                                                        self.USER_LEVEL: 3
                                                        }})
        self.add_inputs(dynamic_inputs)

        dynamic_outputs = {}
        if self.EVAL_OUTPUTS in disc_in:
            _vars_to_gather = self.get_sosdisc_inputs(self.EVAL_OUTPUTS)
            # we fetch the inputs and outputs selected by the user
            vars_to_gather = _vars_to_gather[_vars_to_gather['selected_output'] == True]
            selected_outputs = vars_to_gather['full_name'].values.tolist()
            outputs_names = vars_to_gather['output_name'].values.tolist()
            self._clear_gather_names()
            for out_var, out_name in zip(selected_outputs, outputs_names):
                _out_name = out_name or f'{out_var}{self.GATHER_DEFAULT_SUFFIX}'
                # Val : Possibility to add subtype for dict with output type maybe ?
                dynamic_outputs.update(
                    {_out_name: {self.TYPE: 'dict',
                                 self.VISIBILITY: 'Shared',
                                 self.NAMESPACE: self.NS_EVAL}})
                self._set_gather_names(out_var, _out_name)
                # TODO: Disc1.indicator_dict is shown as indicator_dict on GUI and it is not desired behaviour

        # so that eventual mono-instance outputs get clear
        if self.builder_tool is not None:
            dynamic_output_from_tool = self.builder_tool.get_dynamic_output_from_tool()
            dynamic_outputs.update(dynamic_output_from_tool)

        self.add_outputs(dynamic_outputs)

    def configure_tool(self):
        '''
        Instantiate the tool if it does not and prepare it with data that he needs (the tool know what he needs)
        '''
        if self.builder_tool is None:
            builder_tool_cls = self.ee.factory.create_scatter_tool_builder(
                'scatter_tool', map_name=self.map_name,
                display_options=self.display_options)
            self.builder_tool = builder_tool_cls.instantiate()
            self.builder_tool.associate_tool_to_driver(
                self, cls_builder=self.cls_builder, associated_namespaces=self.associated_namespaces)
        self.scatter_list_valid, self.scatter_list_integrity_msg = self.check_scatter_list_validity()
        if self.scatter_list_valid:
            self.builder_tool.prepare_tool()
        else:
            self.logger.error(self.scatter_list_integrity_msg)

    def build_tool(self):
        if self.builder_tool is not None and self.scatter_list_valid:
            self.builder_tool.build()

    def check_scatter_list_validity(self):
        # checking for duplicates
        msg = ''
        if self.SCENARIO_DF in self.get_data_in():
            scenario_df = self.get_sosdisc_inputs(self.SCENARIO_DF)
            scenario_names = scenario_df[scenario_df[self.SELECTED_SCENARIO]
                                         == True][self.SCENARIO_NAME].values.tolist()
            set_sc_names = set(scenario_names)
            if len(scenario_names) != len(set_sc_names):
                repeated_elements = [
                    sc for sc in set_sc_names if scenario_names.count(sc) > 1]
                msg = 'Cannot activate several scenarios with the same name (' + \
                      repeated_elements[0]
                for sc in repeated_elements[1:]:
                    msg += ', ' + sc
                msg += ').'
                return False, msg
        # in any other case the list is valid
        return True, msg

    def subprocesses_built(self, scenario_names):
        """
        Check whether the subproxies built are coherent with the input list scenario_names.

        Arguments:
            scenario_names (list[string]): expected names of the subproxies.
        """
        if self.flatten_subprocess and self.builder_tool:
            proxies_names = self.builder_tool.get_all_built_disciplines_names()
        else:
            proxies_names = [disc.sos_name for disc in self.scenarios]
        # # assuming self.coupling_per_scenario is true so bock below commented
        # if self.coupling_per_scenario:
        #     builder_names = [b.sos_name for b in self.cls_builder]
        #     expected_proxies_names = []
        #     for sc_name in scenario_names:
        #         for builder_name in builder_names:
        #             expected_proxies_names.append(self.ee.ns_manager.compose_ns([sc_name, builder_name]))
        #     return set(expected_proxies_names) == set(proxies_names)
        # else:
        # return set(proxies_names) == set(scenario_names)
        return proxies_names != [] and set(proxies_names) == set(scenario_names)

    def prepare_variables_to_propagate(self):
        # TODO: code below might need refactoring after reference_scenario
        # configuration fashion is decided upon
        scenario_df = self.get_sosdisc_inputs(self.SCENARIO_DF)
        instance_reference = self.get_sosdisc_inputs(self.INSTANCE_REFERENCE)
        # sce_df = copy.deepcopy(scenario_df)

        if instance_reference:
            # Addition of Reference Scenario
            scenario_df = scenario_df.append(
                {self.SELECTED_SCENARIO: True,
                 self.SCENARIO_NAME: self.REFERENCE_SCENARIO_NAME},
                ignore_index=True)
        # NB assuming that the scenario_df entries are unique otherwise there
        # is some intelligence to be added
        scenario_names = scenario_df[scenario_df[self.SELECTED_SCENARIO]
                                     == True][self.SCENARIO_NAME].values.tolist()
        trade_vars = []
        # check that all the input scenarios have indeed been built
        # (configuration sequence allows the opposite)
        if self.subprocesses_built(scenario_names):
            trade_vars = [col for col in scenario_df.columns if col not in
                          [self.SELECTED_SCENARIO, self.SCENARIO_NAME]]
        return scenario_df, instance_reference, trade_vars, scenario_names

    def _clear_gather_names(self):
        """
        Clear attributes gather_names and gather_out_keys used for multi-instance gather capabilities.
        """
        self.gather_names = {}
        self.gather_out_keys = []

    def _set_gather_names(self, var_name, output_out_name):
        """
        Build a dictionary var_full_name : (output_name, scenario_name) to facilitate gather capabilities and gathered
        variable storage. This is done one variable at a time.

        Arguments:
            var_name: full name of variable to gather anonymized wrt scenario name node
            output_out_name: full name of output gather variable anonymized wrt output namespace node
        """

        self.gather_out_keys.append(output_out_name)

        gather_names_for_var = {}
        disc_in = self.get_data_in()
        if self.SCENARIO_DF in disc_in:
            driver_evaluator_ns = self.get_disc_full_name()
            scenario_df = self.get_sosdisc_inputs(self.SCENARIO_DF)
            scenario_names = scenario_df[scenario_df[self.SELECTED_SCENARIO] == True][
                self.SCENARIO_NAME].values.tolist()

            for sc in scenario_names:
                var_full_name = self.ee.ns_manager.compose_ns(
                    [driver_evaluator_ns, sc, var_name])
                gather_names_for_var[var_full_name] = (output_out_name, sc)
        self.gather_names.update(gather_names_for_var)

    def configure_subprocesses_with_driver_input(self):
        """
        This method forces the trade variables values of the subprocesses in function of the driverevaluator input df.
        """

        scenario_df, instance_reference, trade_vars, scenario_names = self.prepare_variables_to_propagate()
        # PROPAGATE NON-TRADE VARIABLES VALUES FROM REFERENCE TO SUBDISCIPLINES
        if self.subprocesses_built(scenario_names):
            # CHECK USECASE IMPORT AND IMPORT IT IF NEEDED
            # PROPAGATE NON-TRADE VARIABLES VALUES FROM REFERENCE TO
            # SUBDISCIPLINES
            # if self.sos_name == 'inner_ms':
            #     print('dfqsfdqs')
            if instance_reference:
                scenario_names = scenario_names[:-1]
                ref_discipline = self.scenarios[self.get_reference_scenario_index(
                )]

                # ref_discipline_full_name =
                # ref_discipline.get_disc_full_name() # do provide the sting
                # path of data in flatten
                driver_evaluator_ns = self.get_disc_full_name()
                reference_scenario_ns = self.ee.ns_manager.compose_ns(
                    [driver_evaluator_ns, self.REFERENCE_SCENARIO_NAME])
                # ref_discipline_full_name may need to be renamed has it is not
                # true in flatten mode
                ref_discipline_full_name = reference_scenario_ns

                # Manage usecase import
                self.manage_import_inputs_from_sub_process(
                    ref_discipline_full_name)
                ref_changes_dict, ref_dict = self.get_reference_non_trade_variables_changes(
                    trade_vars)

                scenarios_non_trade_vars_dict = self.transform_dict_from_reference_to_other_scenarios(ref_discipline,
                                                                                                      scenario_names,
                                                                                                      ref_dict)

                # Update of original editability state in case modification
                # scenario df
                if (not set(scenario_names) == set(self.old_scenario_names)) and self.old_scenario_names != []:
                    new_scenarios = set(scenario_names) - set(self.old_scenario_names)
                    self.there_are_new_scenarios = True
                    for new_scenario in new_scenarios:
                        new_scenario_non_trade_vars_dict = {key: value
                                                            for key, value in scenarios_non_trade_vars_dict.items()
                                                            if new_scenario in key}

                        new_scenario_editable_dict = self.save_original_editable_attr_from_non_trade_variables(
                            new_scenario_non_trade_vars_dict)
                        self.original_editable_dict_non_ref.update(
                            new_scenario_editable_dict)
                self.old_scenario_names = scenario_names

                # Save the original editability state in case reference is
                # un-instantiated.
                self.save_original_editability_state(
                    ref_dict, scenarios_non_trade_vars_dict)
                # Modification of read-only or editable depending on
                # LINKED_MODE or COPY_MODE
                self.modify_editable_attribute_according_to_reference_mode(
                    scenarios_non_trade_vars_dict)
                # Propagation to other scenarios if necessary
                self.propagate_reference_non_trade_variables(
                    ref_changes_dict, ref_dict, ref_discipline, scenario_names)
            else:
                if self.original_editable_dict_non_ref:
                    for sc in scenario_names:
                        for key in self.original_editable_dict_non_ref.keys():
                            if sc in key:
                                self.ee.dm.set_data(
                                    key, 'editable', self.original_editable_dict_non_ref[key])

            # PROPAGATE TRADE VARIABLES VALUES FROM scenario_df
            # check that there are indeed variable changes input, with respect
            # to reference scenario
            if trade_vars:
                driver_evaluator_ns = self.ee.ns_manager.get_local_namespace_value(
                    self)
                scenarios_data_dict = {}
                for sc in scenario_names:
                    # assuming it is unique
                    sc_row = scenario_df[scenario_df[self.SCENARIO_NAME]
                                         == sc].iloc[0]
                    for var in trade_vars:
                        var_full_name = self.ee.ns_manager.compose_ns(
                            [driver_evaluator_ns, sc, var])
                        scenarios_data_dict[var_full_name] = sc_row.loc[var]
                if scenarios_data_dict and self.subprocess_is_configured():
                    # push to dm
                    # TODO: should also alter associated disciplines' reconfig.
                    # flags for structuring ? TO TEST
                    self.ee.dm.set_values_from_dict(scenarios_data_dict)
                    # self.ee.load_study_from_input_dict(scenarios_data_dict)

    # def set_reference_trade_variables_in_scenario_df(self, sce_df):
    #
    #     var_names = [col for col in sce_df.columns if col not in
    #                  [self.SELECTED_SCENARIO, self.SCENARIO_NAME]]
    #
    #     index_ref_disc = self.get_reference_scenario_index()
    #     for var in var_names:
    #         short_name_var = var.split(".")[-1]
    #         for subdisc in self.proxy_disciplines[index_ref_disc].proxy_disciplines:
    #             if short_name_var in subdisc.get_data_in():
    #                 value_var = subdisc.get_sosdisc_inputs(short_name_var)
    #                 sce_df.at[sce_df.loc[sce_df[self.SCENARIO_NAME] == 'ReferenceScenario'].index, var] = value_var
    #
    #     return sce_df
    # def set_reference_trade_variables_in_scenario_df(self, sce_df):
    #
    #     var_names = [col for col in sce_df.columns if col not in
    #                  [self.SELECTED_SCENARIO, self.SCENARIO_NAME]]
    #
    #     index_ref_disc = self.get_reference_scenario_index()
    #     # for var in var_names:
    #     #    short_name_var = var.split(".")[-1]
    #     #    for subdisc in self.proxy_disciplines[index_ref_disc].proxy_disciplines:
    #     #        if short_name_var in subdisc.get_data_in():
    #     #            value_var = subdisc.get_sosdisc_inputs(short_name_var)
    #     #            sce_df.at[sce_df.loc[sce_df[self.SCENARIO_NAME]
    #     #                                 == 'ReferenceScenario'].index, var] = value_var
    #     # TODO
    #     # This is with error in case value_var is a list-like object (numpy array, list, set, tuple etc.)
    #     # https://stackoverflow.com/questions/48000225/must-have-equal-len-keys-and-value-when-setting-with-an-iterable
    #     # Example variable z = array([1., 1.]) of sellar put in trade variables
    #     return sce_df

    # These dicts are of non-trade variables
    def save_original_editability_state(self, ref_dict, non_ref_dict):

        if self.save_editable_attr:
            # self.original_editable_dict_ref = self.save_original_editable_attr_from_non_trade_variables(
            #     ref_dict)
            self.original_editable_dict_non_ref = self.save_original_editable_attr_from_non_trade_variables(
                non_ref_dict)
            # self.original_editability_dict = self.original_editable_dict_ref | self.original_editable_dict_non_ref
            # self.original_editability_dict = {**self.original_editable_dict_ref,
            #                                   **self.original_editable_dict_non_ref}
            self.save_editable_attr = False

    def get_reference_scenario_index(self):
        """
        """
        index_ref = 0
        my_root = self.ee.ns_manager.compose_ns(
            [self.sos_name, self.REFERENCE_SCENARIO_NAME])

        for disc in self.scenarios:
            if disc.sos_name == self.REFERENCE_SCENARIO_NAME \
                    or my_root in disc.sos_name:  # for flatten_subprocess
                # TODO: better implement this 2nd condition ?
                break
            else:
                index_ref += 1
        return index_ref

    def check_if_there_are_reference_variables_changes(self):

        scenario_df, instance_reference, trade_vars, scenario_names = self.prepare_variables_to_propagate()

        ref_changes_dict = {}
        if self.subprocesses_built(scenario_names):
            if instance_reference:
                ref_changes_dict, ref_dict = self.get_reference_non_trade_variables_changes(
                    trade_vars)

        return ref_changes_dict

    def get_reference_non_trade_variables_changes(self, trade_vars):
        ref_discipline = self.scenarios[self.get_reference_scenario_index()]

        # Take reference scenario non-trade variables (num and non-num) and its
        # values
        ref_dict = {}
        for key in ref_discipline.get_input_data_names():
            if all(key.split(self.REFERENCE_SCENARIO_NAME + '.')[-1] != trade_var for trade_var in trade_vars):
                ref_dict[key] = ref_discipline.ee.dm.get_value(key)

        # Check if reference values have changed and select only those which
        # have changed

        ref_changes_dict = {}
        for key in ref_dict.keys():
            if key in self.old_ref_dict.keys():
                if isinstance(ref_dict[key], pd.DataFrame):
                    if not ref_dict[key].equals(self.old_ref_dict[key]):
                        ref_changes_dict[key] = ref_dict[key]
                elif isinstance(ref_dict[key], (np.ndarray)):
                    if not (np.array_equal(ref_dict[key], self.old_ref_dict[key])):
                        ref_changes_dict[key] = ref_dict[key]
                elif isinstance(ref_dict[key], (list)):
                    if not (np.array_equal(ref_dict[key], self.old_ref_dict[key])):
                        ref_changes_dict[key] = ref_dict[key]
                else:
                    if ref_dict[key] != self.old_ref_dict[key]:
                        ref_changes_dict[key] = ref_dict[key]
            else:
                ref_changes_dict[key] = ref_dict[key]

        # TODO: replace the above code by a more general function ...
        # ======================================================================
        # ref_changes_dict = {}
        # if self.old_ref_dict == {}:
        #     ref_changes_dict = ref_dict
        # else:
        #     # See Test 01 of test_69_compare_dict_compute_len
        #     compare_dict(ref_dict, self.old_ref_dict, '',
        #                  ref_changes_dict, df_equals=True)
        #     # We cannot use compare_dict as if: maybe we choude add a diff_compare_dict as an adaptation of compare_dict
        # ======================================================================

        return ref_changes_dict, ref_dict

    def propagate_reference_non_trade_variables(self, ref_changes_dict, ref_dict, ref_discipline,
                                                scenario_names_to_propagate):

        if ref_changes_dict:
            self.old_ref_dict = copy.deepcopy(ref_dict)

        # ref_discipline = self.scenarios[self.get_reference_scenario_index()]

        # Build other scenarios variables and values dict from reference
        dict_to_propagate = {}
        # Propagate all reference
        if self.get_sosdisc_inputs(self.REFERENCE_MODE) == self.LINKED_MODE:
            dict_to_propagate = self.transform_dict_from_reference_to_other_scenarios(ref_discipline,
                                                                                      scenario_names_to_propagate,
                                                                                      ref_dict)
        # Propagate reference changes
        elif self.get_sosdisc_inputs(self.REFERENCE_MODE) == self.COPY_MODE and ref_changes_dict:
            dict_to_propagate = self.transform_dict_from_reference_to_other_scenarios(ref_discipline,
                                                                                      scenario_names_to_propagate,
                                                                                      ref_changes_dict)
        # Propagate other scenarios variables and values
        if self.there_are_new_scenarios:
            if dict_to_propagate:
                self.ee.dm.set_values_from_dict(dict_to_propagate)
        else:
            if ref_changes_dict and dict_to_propagate:
                self.ee.dm.set_values_from_dict(dict_to_propagate)

    def get_other_evaluators_names_and_mode_under_current_one(self):
        other_evaluators_names_and_mode = []
        for disc in self.scenarios:
            name_and_modes = self.search_evaluator_names_and_modify_mode_iteratively(
                disc)
            if name_and_modes != []:
                other_evaluators_names_and_mode.append(name_and_modes)

        return other_evaluators_names_and_mode

    def search_evaluator_names_and_modify_mode_iteratively(self, disc):

        list = []
        for subdisc in disc.proxy_disciplines:
            if subdisc.__class__.__name__ == 'ProxyDriverEvaluator':
                if subdisc.get_sosdisc_inputs(self.INSTANCE_REFERENCE) == True:
                    # If upper ProxyDriverEvaluator is in linked mode, all
                    # lower ProxyDriverEvaluator shall be as well.
                    if self.get_sosdisc_inputs(self.REFERENCE_MODE) == self.LINKED_MODE:
                        subdriver_full_name = self.ee.ns_manager.get_local_namespace_value(
                            subdisc)
                        if 'ReferenceScenario' in subdriver_full_name:
                            self.ee.dm.set_data(
                                subdriver_full_name + '.reference_mode', 'value', self.LINKED_MODE)
                    list = [subdisc.sos_name]
                else:
                    list = [subdisc.sos_name]
            elif subdisc.__class__.__name__ == 'ProxyDiscipline':
                pass
            else:
                name_and_modes = self.search_evaluator_names_and_modify_mode_iteratively(
                    subdisc)
                list.append(name_and_modes)

        return list

    def modify_editable_attribute_according_to_reference_mode(self, scenarios_non_trade_vars_dict):

        other_evaluators_names_and_mode = self.get_other_evaluators_names_and_mode_under_current_one()

        if self.get_sosdisc_inputs(self.REFERENCE_MODE) == self.LINKED_MODE:
            for key in scenarios_non_trade_vars_dict.keys():
                self.ee.dm.set_data(key, 'editable', False)
        elif self.get_sosdisc_inputs(self.REFERENCE_MODE) == self.COPY_MODE:
            for key in scenarios_non_trade_vars_dict.keys():
                if other_evaluators_names_and_mode != []:  # This means there are evaluators under current one
                    for element in other_evaluators_names_and_mode:
                        if element[0] in key:  # Ignore variables from inner ProxyDriverEvaluators
                            pass
                        else:
                            if self.original_editable_dict_non_ref[key] == False:
                                pass
                            else:
                                self.ee.dm.set_data(key, 'editable', True)
                else:
                    if self.original_editable_dict_non_ref[key] == False:
                        pass
                    else:
                        self.ee.dm.set_data(key, 'editable', True)

    def save_original_editable_attr_from_non_trade_variables(self, dict):

        dict_out = {}
        for key in dict:
            dict_out[key] = self.dm.get_data(key, 'editable')

        return dict_out

    def transform_dict_from_reference_to_other_scenarios(self, ref_discipline, scenario_names, dict_from_ref):

        transformed_to_other_scenarios_dict = {}
        for key in dict_from_ref.keys():
            for sc in scenario_names:
                if self.REFERENCE_SCENARIO_NAME in key and self.sos_name in key:
                    new_key = key.split(self.sos_name, 1)[0] + self.sos_name + '.' + sc + \
                              key.split(self.sos_name,
                                        1)[-1].split(self.REFERENCE_SCENARIO_NAME, 1)[-1]
                elif self.REFERENCE_SCENARIO_NAME in key and not self.sos_name in key:
                    new_key = key.split(self.REFERENCE_SCENARIO_NAME, 1)[
                                  0] + sc + key.split(self.REFERENCE_SCENARIO_NAME, 1)[-1]
                else:
                    new_key = key
                if self.dm.check_data_in_dm(new_key):
                    transformed_to_other_scenarios_dict[new_key] = dict_from_ref[key]

        return transformed_to_other_scenarios_dict

        # # Take non-trade variables values from subdisciplines of reference scenario
        # for subdisc in self.proxy_disciplines[index_ref_disc].proxy_disciplines:
        #     if subdisc.__class__.__name__ == 'ProxyDiscipline':
        #         # For ProxyDiscipline --> Propagation of non-trade variables
        #         self.propagate_non_trade_variables_of_proxy_discipline(subdisc, trade_vars)
        #     elif subdisc.__class__.__name__ == 'ProxyDriverEvaluator':
        #         # For ProxyDriverEvaluator --> Propagation of non-trade variables from ReferenceScenario (recursivity)
        #         subdisc.set_non_trade_variables_from_reference_scenario(trade_vars)
        #     else:
        #         # For ProxyCoupling... --> Propagation of its subdisciplines variables (recursively)
        #         self.propagate_non_trade_variables_of_proxy_coupling(subdisc, trade_vars)

    # def propagate_non_trade_variables_of_proxy_discipline(self, subdiscipline, trade_vars):
    #
    #     non_trade_var_dict_ref_to_propagate = {}
    #     non_trade_var_dict_not_ref_scenario = {}
    #     # Get non-numerical variables full name and values from reference
    #     non_num_var_dict = subdiscipline.get_non_numerical_variables_and_values_dict()
    #
    #     # If non-numerical variables have been set, select non-trade variables from them
    #     if all(value == None for value in non_num_var_dict.values()):
    #         pass
    #     else:
    #         for key in non_num_var_dict:  # Non-numerical variables
    #             if all(key.split('.ReferenceScenario.')[-1] != trade_var for trade_var in
    #                    trade_vars):  # Here non-trade variables are taken from non-numerical values
    #                 non_trade_var_dict_ref_to_propagate[key] = non_num_var_dict[key]
    #
    #     # Adapt non-trade variables and values from reference to full name of other scenarios
    #     if non_trade_var_dict_ref_to_propagate:
    #         for key in non_trade_var_dict_ref_to_propagate.keys():
    #             for sc in self.scenario_names[:-1]:
    #                 if 'ReferenceScenario' in key:
    #                     new_key = key.rsplit('ReferenceScenario', 1)[0] + sc + key.rsplit('ReferenceScenario', 1)[-1]
    #                     # new_key = driver_evaluator_ns + "." + sc + key.split('ReferenceScenario')[-1]
    #                 else:
    #                     new_key = key
    #                 non_trade_var_dict_not_ref_scenario[new_key] = non_trade_var_dict_ref_to_propagate[key]
    #
    #     if non_trade_var_dict_not_ref_scenario:
    #         self.ee.dm.set_values_from_dict(non_trade_var_dict_not_ref_scenario)
    #
    # def propagate_non_trade_variables_of_proxy_coupling(self, subcoupling, trade_vars):
    #     for subsubdisc in subcoupling.proxy_disciplines:
    #         if subsubdisc.__class__.__name__ == 'ProxyDiscipline':
    #             # For ProxyDiscipline --> Propagation of non-trade variables
    #             self.propagate_non_trade_variables_of_proxy_discipline(subsubdisc, trade_vars)
    #         elif subsubdisc.__class__.__name__ == 'ProxyDriverEvaluator':
    #             # For ProxyDriverEvaluator --> Propagation of non-trade variables from ReferenceScenario (recursivity)
    #             subsubdisc.set_non_trade_variables_from_reference_scenario(trade_vars)
    #         else:
    #             # For ProxyCoupling... --> Propagation of its subdisciplines variables (recursively)
    #             self.propagate_non_trade_variables_of_proxy_coupling(subsubdisc, trade_vars)

    #######################################
    #######################################
    ##### MONO-INSTANCE MODE METHODS ######
    #######################################
    #######################################

    def prepare_mono_instance_build(self):
        '''
        Get the builder of the single subprocesses in mono-instance builder mode.
        '''
        if self.eval_process_builder is None:
            self._set_eval_process_builder()

        return [self.eval_process_builder] if self.eval_process_builder is not None else []

    def get_x0(self):
        '''
        Get initial values for input values decided in the evaluation
        '''

        return dict(zip(self.eval_in_list,
                        map(self.dm.get_value, self.eval_in_list)))

    def _get_dynamic_inputs_doe(self, disc_in, selected_inputs_has_changed):
        default_custom_dataframe = pd.DataFrame(
            [[NaN for _ in range(len(self.selected_inputs))]], columns=self.selected_inputs)
        dataframe_descriptor = {}
        for i, key in enumerate(self.selected_inputs):
            var_f_name = self.eval_in_list[i]
            if var_f_name in self.ee.dm.data_id_map:
                var = tuple([self.ee.dm.get_data(
                    var_f_name, self.TYPE), None, True])
                dataframe_descriptor[key] = var
            elif self.MULTIPLIER_PARTICULE in var_f_name:
                # for multipliers assume it is a float
                dataframe_descriptor[key] = ('float', None, True)
            else:
                raise KeyError(f'Selected input {var_f_name} is not in the Data Manager')

        dynamic_inputs = {'samples_df': {self.TYPE: 'dataframe', self.DEFAULT: default_custom_dataframe,
                                         self.DATAFRAME_DESCRIPTOR: dataframe_descriptor,
                                         self.DATAFRAME_EDITION_LOCKED: False,
                                         self.VISIBILITY: SoSWrapp.SHARED_VISIBILITY,
                                         self.NAMESPACE: self.NS_EVAL
                                         }}

        # This reflects 'samples_df' dynamic input has been configured and that
        # eval_inputs have changed
        if 'samples_df' in disc_in and selected_inputs_has_changed:

            if disc_in['samples_df']['value'] is not None:
                from_samples = list(disc_in['samples_df']['value'].keys())
                from_eval_inputs = list(default_custom_dataframe.keys())
                final_dataframe = pd.DataFrame(
                    None, columns=self.selected_inputs)

                len_df = 1
                for element in from_eval_inputs:
                    if element in from_samples:
                        len_df = len(disc_in['samples_df']['value'])

                for element in from_eval_inputs:
                    if element in from_samples:
                        final_dataframe[element] = disc_in['samples_df']['value'][element]

                    else:
                        final_dataframe[element] = [NaN for _ in range(len_df)]

                disc_in['samples_df'][self.VALUE] = final_dataframe
            disc_in['samples_df'][self.DATAFRAME_DESCRIPTOR] = dataframe_descriptor
        return dynamic_inputs

    def _set_eval_process_builder(self):
        '''
        Create the eval process builder, in a coupling if necessary, which will allow mono-instance builds.
        '''
        updated_ns_list = self.update_sub_builders_namespaces()
        if len(self.cls_builder) == 0:  # added condition for proc build
            disc_builder = None
        elif len(self.cls_builder) == 1:
            # Note no distinction is made whether the builder is executable or not; old implementation used to put
            # scatter builds under a coupling automatically too.
            disc_builder = self.cls_builder[0]
        else:
            # If eval process is a list of builders then we build a coupling
            # containing the eval process
            if self.flatten_subprocess:
                disc_builder = None
            else:
                disc_builder = self.create_sub_builder_coupling(
                    self.SUBCOUPLING_NAME, self.cls_builder)
                self.hide_coupling_in_driver_for_display(disc_builder)

        self.eval_process_builder = disc_builder

        self.eval_process_builder.add_namespace_list_in_associated_namespaces(
            updated_ns_list)

    def update_sub_builders_namespaces(self):
        '''
        Update sub builders namespaces with the driver name in monoinstance case
        '''

        ns_ids_list = []
        extra_name = f'{self.sos_name}'
        after_name = self.father_executor.get_disc_full_name()

        for ns_name in self.sub_builder_namespaces:
            old_ns = self.ee.ns_manager.get_ns_in_shared_ns_dict(ns_name)
            updated_value = self.ee.ns_manager.update_ns_value_with_extra_ns(
                old_ns.get_value(), extra_name, after_name=after_name)
            display_value = old_ns.get_display_value_if_exists()
            ns_id = self.ee.ns_manager.add_ns(
                ns_name, updated_value, display_value=display_value, add_in_shared_ns_dict=False)
            ns_ids_list.append(ns_id)

        return ns_ids_list

    def hide_coupling_in_driver_for_display(self, disc_builder):
        '''
        Set the display_value of the sub coupling to the display_value of the driver
        (if no display_value filled the display_value is the simulation value)
        '''
        driver_display_value = self.ee.ns_manager.get_local_namespace(
            self).get_display_value()
        self.ee.ns_manager.add_display_ns_to_builder(
            disc_builder, driver_display_value)

    def set_eval_in_out_lists(self, in_list, out_list, inside_evaluator=False):
        '''
        Set the evaluation variable list (in and out) present in the DM
        which fits with the eval_in_base_list filled in the usecase or by the user
        '''

        # final_in_list, final_out_list = self.remove_pseudo_variables(in_list, out_list) # only actual subprocess variables
        if in_list is not None:
            self.eval_in_list = [
                f'{self.get_disc_full_name()}.{element}' for element in in_list]
        self.eval_out_list = [
            f'{self.get_disc_full_name()}.{element}' for element in out_list]

    # def remove_pseudo_variables(self, in_list, out_list):
    #     # and add the real variables that will be used as reference variables or MorphMatrix combinations
    #     # in this case managing only multiplier particles
    #     new_in_list = []
    #     for element in in_list:
    #         if self.MULTIPLIER_PARTICULE in element:
    #             if '@' in element:
    #                 new_in_list.append(element.rsplit('@', 1)[0])
    #             else:
    #                 new_in_list.append(element.rsplit(self.MULTIPLIER_PARTICULE, 1)[0])
    #         else:
    #             new_in_list.append(element)
    #     return new_in_list, out_list

    def set_eval_possible_values(self, io_type_in=True, io_type_out=True, strip_first_ns=False):
        '''
        Check recursively the disciplines in the subprocess in order to detect their inputs and outputs.
        Once all disciplines have been run through, set the possible values for eval_inputs and eval_outputs in the DM
        These are the variables names anonymized wrt driver-evaluator node (mono-instance) or scenario node
        (multi-instance).

        Arguments:
            io_type_in (bool): whether to take inputs into account
            io_type_out (bool): whether to take outputs into account
            strip_first_ns (bool): whether to strip the scenario name (multi-instance case) from the variable name
        '''

        possible_in_values, possible_out_values = set(), set()
        # scenarios contains all the built sub disciplines (proxy_disciplines does NOT in flatten mode)
        for scenario_disc in self.scenarios:
            analyzed_disc = scenario_disc
            possible_in_values_full, possible_out_values_full = self.fill_possible_values(
                analyzed_disc, io_type_in=io_type_in, io_type_out=io_type_out)
            possible_in_values_full, possible_out_values_full = self.find_possible_values(analyzed_disc,
                                                                                          possible_in_values_full,
                                                                                          possible_out_values_full,
                                                                                          io_type_in=io_type_in,
                                                                                          io_type_out=io_type_out)
            # strip the scenario name to have just one entry for repeated variables in scenario instances
            if strip_first_ns:
                possible_in_values_full = [_var.split('.', 1)[-1] for _var in possible_in_values_full]
                possible_out_values_full = [_var.split('.', 1)[-1] for _var in possible_out_values_full]
            possible_in_values.update(possible_in_values_full)
            possible_out_values.update(possible_out_values_full)

        disc_in = self.get_data_in()
        if possible_in_values and io_type_in:

            # Convert sets into lists
            possible_in_values = list(possible_in_values)
            # these sorts are just for aesthetics
            possible_in_values.sort()
            default_in_dataframe = pd.DataFrame({'selected_input': [False for _ in possible_in_values],
                                                 'full_name': possible_in_values})

            eval_input_new_dm = self.get_sosdisc_inputs(self.EVAL_INPUTS)
            eval_inputs_f_name = self.get_var_full_name(self.EVAL_INPUTS, disc_in)

            if eval_input_new_dm is None:
                self.dm.set_data(eval_inputs_f_name,
                                 'value', default_in_dataframe, check_value=False)
            # check if the eval_inputs need to be updated after a subprocess
            # configure
            elif set(eval_input_new_dm['full_name'].tolist()) != (set(default_in_dataframe['full_name'].tolist())):
                self.check_eval_io(eval_input_new_dm['full_name'].tolist(), default_in_dataframe['full_name'].tolist(),
                                   is_eval_input=True)
                default_dataframe = copy.deepcopy(default_in_dataframe)
                already_set_names = eval_input_new_dm['full_name'].tolist()
                already_set_values = eval_input_new_dm['selected_input'].tolist()
                for index, name in enumerate(already_set_names):
                    default_dataframe.loc[default_dataframe['full_name'] == name, 'selected_input'] = already_set_values[
                        index]  # this will filter variables that are not inputs of the subprocess
                    if self.MULTIPLIER_PARTICULE in name:
                        default_dataframe = default_dataframe.append(
                            pd.DataFrame({'selected_input': [already_set_values[index]],
                                          'full_name': [name]}), ignore_index=True)
                self.dm.set_data(eval_inputs_f_name,
                                 'value', default_dataframe, check_value=False)

        if possible_out_values and io_type_out:
            possible_out_values = list(possible_out_values)
            possible_out_values.sort()
            default_out_dataframe = pd.DataFrame({'selected_output': [False for _ in possible_out_values],
                                                  'full_name': possible_out_values,
                                                  'output_name': [None for _ in possible_out_values]})
            eval_output_new_dm = self.get_sosdisc_inputs(self.EVAL_OUTPUTS)
            eval_outputs_f_name = self.get_var_full_name(self.EVAL_OUTPUTS, disc_in)
            if eval_output_new_dm is None:
                self.dm.set_data(eval_outputs_f_name,
                                 'value', default_out_dataframe, check_value=False)
            # check if the eval_inputs need to be updated after a subprocess configure
            elif set(eval_output_new_dm['full_name'].tolist()) != (set(default_out_dataframe['full_name'].tolist())):
                self.check_eval_io(eval_output_new_dm['full_name'].tolist(), default_out_dataframe['full_name'].tolist(),
                                   is_eval_input=False)
                default_dataframe = copy.deepcopy(default_out_dataframe)
                already_set_names = eval_output_new_dm['full_name'].tolist()
                already_set_values = eval_output_new_dm['selected_output'].tolist()
                if 'output_name' in eval_output_new_dm.columns:
                    # TODO: maybe better to repair tests than to accept default, in particular for data integrity check
                    already_set_out_names = eval_output_new_dm['output_name'].tolist()
                else:
                    already_set_out_names = [None for _ in already_set_names]
                for index, name in enumerate(already_set_names):
                    default_dataframe.loc[default_dataframe['full_name'] == name,
                    ['selected_output', 'output_name']] = \
                        (already_set_values[index], already_set_out_names[index])
                self.dm.set_data(eval_outputs_f_name,
                                 'value', default_dataframe, check_value=False)
