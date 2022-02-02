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
# coding: utf-8

from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, TwoAxesInstanciatedChart
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
import numpy as np

import pandas as pd
from copy import deepcopy
from climateeconomics.core.core_witness.policy_model import PolicyModel
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline


class PolicyDiscipline(SoSDiscipline):
    _maturity = 'Research'

    years = np.arange(2020, 2101)
    DESC_IN = {
        'year_start': {'type': 'int', 'default': 2020, 'possible_values': years, 'unit': 'year', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'year_end': {'type': 'int', 'default': 2100, 'possible_values': years, 'unit': 'year', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'CCS_price': {'type': 'dataframe', 'unit': '$/tCO2', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'CO2_damage_price': {'type': 'dataframe', 'unit': '$/tCO2', 'visibility': SoSDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
    }

    DESC_OUT = {
        'CO2_taxes': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'}

    }

    def init_execution(self):
        param_in = self.get_sosdisc_inputs()
        self.policy_model = PolicyModel()

    def run(self):
        param_in = self.get_sosdisc_inputs()

        self.policy_model.compute_smax(param_in)
        dict_values = {
            'CO2_taxes': self.policy_model.CO2_tax}

        # store data
        self.store_sos_outputs_values(dict_values)

    def compute_sos_jacobian(self):
        """ 
        Compute sos jacobian
        """

        dCO2_tax_dCO2_damage, dCO2_tax_dCCS_price = self.policy_model.compute_CO2_tax_dCCS_dCO2_damage_smooth()

        self.set_partial_derivative_for_other_types(
            ('CO2_taxes', 'CO2_tax'), ('CO2_damage_price', 'CO2_damage_price'),  np.identity(len(dCO2_tax_dCO2_damage)) * np.array(dCO2_tax_dCO2_damage))

        self.set_partial_derivative_for_other_types(
            ('CO2_taxes', 'CO2_tax'), ('CCS_price', 'ccs_price_per_tCO2'),  np.identity(len(dCO2_tax_dCCS_price)) * np.array(dCO2_tax_dCCS_price))

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = ['CO2 tax']
        # First filter to deal with the view : program or actor
        chart_filters.append(ChartFilter(
            'Charts', chart_list, chart_list, 'charts'))

        return chart_filters

    def get_post_processing_list(self, chart_filters=None):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        instanciated_charts = []

        # Overload default value with chart filter
        if chart_filters is not None:
            for chart_filter in chart_filters:
                if chart_filter.filter_key == 'charts':
                    chart_list = chart_filter.selected_values
        if 'CO2 tax' in chart_list:
            CCS_price = self.get_sosdisc_inputs('CCS_price')
            CO2_damage_price = self.get_sosdisc_inputs('CO2_damage_price')
            CO2_tax = self.get_sosdisc_outputs('CO2_taxes')
            years = list(CCS_price['years'].values)

            chart_name = 'CO2 tax chart'

            new_chart = TwoAxesInstanciatedChart('years', 'CO2 tax ($/tCO2)',

                                                 chart_name=chart_name)

            new_series = InstanciatedSeries(
                years, list(CCS_price['ccs_price_per_tCO2'].values), 'CCS price', 'lines')

            new_series2 = InstanciatedSeries(
                years, list(CO2_damage_price['CO2_damage_price'].values), 'CO2 damage', 'lines')

            new_series3 = InstanciatedSeries(
                years, list(CO2_tax['CO2_tax'].values), 'CO2 tax', 'lines')

            new_chart.series.append(new_series)
            new_chart.series.append(new_series2)
            new_chart.series.append(new_series3)

            instanciated_charts.append(new_chart)

        return instanciated_charts