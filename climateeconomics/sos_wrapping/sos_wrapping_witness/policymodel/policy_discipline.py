'''
Copyright 2022 Airbus SAS
Modifications on 2023/06/14-2023/11/03 Copyright 2023 Capgemini

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

from climateeconomics.core.core_witness.climateeco_discipline import ClimateEcoDiscipline
from climateeconomics.core.core_witness.policy_model import PolicyModel
from climateeconomics.glossarycore import GlossaryCore
from sostrades_core.execution_engine.sos_wrapp import SoSWrapp
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sostrades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, \
    TwoAxesInstanciatedChart


# coding: utf-8


class PolicyDiscipline(SoSWrapp):

    # ontology information
    _ontology_data = {
        'label': 'Policy Model',
        'type': 'Research',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fas fa-balance-scale fa-fw',
        'version': '',
    }
    _maturity = 'Research'

    years = np.arange(2020, 2101)
    DESC_IN = {
        GlossaryCore.YearStart: ClimateEcoDiscipline.YEAR_START_DESC_IN,
        GlossaryCore.YearEnd: ClimateEcoDiscipline.YEAR_END_DESC_IN,
        'CCS_price': {'type': 'dataframe', 'unit': '$/tCO2', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_witness',
                      'dataframe_descriptor':
                          {
                              GlossaryCore.Years: ('float', None, False),
                              'ccs_price_per_tCO2': ('float', None, True),
                          }
                      },
        'CO2_damage_price': {'type': 'dataframe', 'unit': '$/tCO2', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_witness',
                             'dataframe_descriptor':
                                 {
                                     GlossaryCore.Years: ('float', None, False),
                                     'CO2_damage_price': ('float', None, True),
                                 }
                             },
        'ccs_price_percentage': {'type': 'float', 'default': 100., 'unit': '%',
                                   'visibility': SoSWrapp.SHARED_VISIBILITY,
                                   'namespace': 'ns_witness', 'user_level': 2},
        'co2_damage_price_percentage': {'type': 'float', 'default': 100., 'unit': '%',
                                   'visibility': SoSWrapp.SHARED_VISIBILITY,
                                   'namespace': 'ns_witness', 'user_level': 2},
    }

    DESC_OUT = {
        GlossaryCore.CO2TaxesValue: {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness', 'unit': '$/tCO2'}

    }

    def init_execution(self):
        param_in = self.get_sosdisc_inputs()
        self.policy_model = PolicyModel()

    def run(self):
        param_in = self.get_sosdisc_inputs()

        self.policy_model.compute_smax(param_in)
        dict_values = {
            GlossaryCore.CO2TaxesValue: self.policy_model.CO2_tax}

        # store data
        self.store_sos_outputs_values(dict_values)

    def compute_sos_jacobian(self):
        """ 
        Compute sos jacobian
        """

        dCO2_tax_dCO2_damage, dCO2_tax_dCCS_price = self.policy_model.compute_CO2_tax_dCCS_dCO2_damage_smooth()

        self.set_partial_derivative_for_other_types(
            (GlossaryCore.CO2TaxesValue, GlossaryCore.CO2Tax), ('CO2_damage_price', 'CO2_damage_price'),  np.identity(len(dCO2_tax_dCO2_damage)) * np.array(dCO2_tax_dCO2_damage))

        self.set_partial_derivative_for_other_types(
            (GlossaryCore.CO2TaxesValue, GlossaryCore.CO2Tax), ('CCS_price', 'ccs_price_per_tCO2'),  np.identity(len(dCO2_tax_dCCS_price)) * np.array(dCO2_tax_dCCS_price))

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
            CO2_tax = self.get_sosdisc_outputs(GlossaryCore.CO2TaxesValue)
            years = list(CCS_price[GlossaryCore.Years].values)

            chart_name = 'CO2 tax chart'

            new_chart = TwoAxesInstanciatedChart(GlossaryCore.Years, 'CO2 tax ($/tCO2)',

                                                 chart_name=chart_name)

            new_series = InstanciatedSeries(
                years, list(CCS_price['ccs_price_per_tCO2'].values), 'CCS price', 'lines')

            new_series2 = InstanciatedSeries(
                years, list(CO2_damage_price['CO2_damage_price'].values), 'CO2 damage', 'lines')

            new_series3 = InstanciatedSeries(
                years, list(CO2_tax[GlossaryCore.CO2Tax].values), 'CO2 tax', 'lines')

            new_chart.series.append(new_series)
            new_chart.series.append(new_series2)
            new_chart.series.append(new_series3)

            instanciated_charts.append(new_chart)

        return instanciated_charts
