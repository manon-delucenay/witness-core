'''
Copyright 2022 Airbus SAS
Modifications on 2023/03/28-2023/11/03 Copyright 2023 Capgemini

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
from copy import deepcopy

import numpy as np
import pandas as pd

from climateeconomics.core.core_witness.climateeco_discipline import ClimateEcoDiscipline
from climateeconomics.core.core_witness.damage_model import DamageModel
from climateeconomics.glossarycore import GlossaryCore
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sostrades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, \
    TwoAxesInstanciatedChart


class DamageDiscipline(ClimateEcoDiscipline):

    # ontology information
    _ontology_data = {
        'label': 'Damage WITNESS Model',
        'type': 'Research',
        'source': 'SoSTrades Project',
        'validated': '',
        'validated_by': 'SoSTrades Project',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fas fa-exclamation-triangle fa-fw',
        'version': '',
    }

    years = np.arange(2020, 2101)
    CO2_tax = np.asarray([500.] * len(years))
    default_CO2_tax = pd.DataFrame(
        {GlossaryCore.Years: years, GlossaryCore.CO2Tax: CO2_tax}, index=years)

    DESC_IN = {
        GlossaryCore.YearStart: ClimateEcoDiscipline.YEAR_START_DESC_IN,
        GlossaryCore.YearEnd: ClimateEcoDiscipline.YEAR_END_DESC_IN,
        GlossaryCore.TimeStep: ClimateEcoDiscipline.TIMESTEP_DESC_IN,
        'init_damag_int': {'type': 'float', 'default': 0.0, 'unit': '-', 'user_level': 3},
        'damag_int': {'type': 'float', 'default': 0.0, 'unit': '-', 'user_level': 3},
        'damag_quad': {'type': 'float', 'default': 0.0022, 'unit': '-', 'user_level': 3},
        'damag_expo': {'type': 'float', 'default': 2.0, 'unit': '-', 'user_level': 3},
        'tipping_point': {'type': 'bool', 'default': True},
        'tp_a1': {'type': 'float', 'visibility': ClimateEcoDiscipline.INTERNAL_VISIBILITY, 'default': 20.46, 'user_level': 3, 'unit': '-'},
        'tp_a2': {'type': 'float', 'visibility': ClimateEcoDiscipline.INTERNAL_VISIBILITY, 'default': 2, 'user_level': 3, 'unit': '-'},
        'tp_a3': {'type': 'float', 'visibility': ClimateEcoDiscipline.INTERNAL_VISIBILITY, 'default': 6.081, 'user_level': 3, 'unit': '-'},
        'tp_a4': {'type': 'float', 'visibility': ClimateEcoDiscipline.INTERNAL_VISIBILITY, 'default': 6.754, 'user_level': 3, 'unit': '-'},
        GlossaryCore.FractionDamageToProductivityValue: {'type': 'float', 'default': 0.30, 'unit': '-', 'visibility': 'Shared', 'namespace': 'ns_witness', 'user_level': 2},
        GlossaryCore.EconomicsDfValue: GlossaryCore.EconomicsDf,
        GlossaryCore.TemperatureDfValue: GlossaryCore.TemperatureDf,
        'total_emissions_damage_ref': {'type': 'float', 'default': 18.0, 'unit': 'Gt', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
                                       'namespace': 'ns_ref', 'user_level': 2},
        'damage_constraint_factor': {'type': 'array', 'unit': '-', 'user_level': 2},
        'assumptions_dict': ClimateEcoDiscipline.ASSUMPTIONS_DESC_IN
    }

    DESC_OUT = {
        'CO2_damage_price': {'type': 'dataframe', 'unit': '$/tCO2', 'visibility': 'Shared', 'namespace': 'ns_witness'},
        GlossaryCore.DamageDf['var_name']: GlossaryCore.DamageDf,
        'expected_damage_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'}
    }

    _maturity = 'Research'

    def init_execution(self):
        in_dict = self.get_sosdisc_inputs()
        self.model = DamageModel(in_dict)

    def setup_sos_disciplines(self):
        """
        Check if flag 'compute_climate_impact_on_gdp' is on or not.
        If so, then the output GlossaryCore.DamageDf['var_name' is shared with other disciplines that requires it as input,
        else it is not, and therefore others discipline will demand to specify t input
        """

        dynamic_outputs = {}

        self.add_outputs(dynamic_outputs)

        self.update_default_with_years()

    def update_default_with_years(self):
        '''
        Update all default dataframes with years 
        '''
        if GlossaryCore.YearStart in self.get_data_in():
            year_start, year_end = self.get_sosdisc_inputs(
                [GlossaryCore.YearStart, GlossaryCore.YearEnd])
            years = np.arange(year_start, year_end + 1)
            damage_constraint_factor_default = np.concatenate(
                (np.linspace(1.0, 1.0, 20), np.asarray([1] * (len(years) - 20))))
            self.set_dynamic_default_values(
                {'damage_constraint_factor': damage_constraint_factor_default})

    def run(self):
        ''' pyworld3 execution '''
        # get inputs
        in_dict = self.get_sosdisc_inputs()
        economics_df = in_dict.pop(GlossaryCore.EconomicsDfValue)
        temperature_df = in_dict.pop\
            (GlossaryCore.TemperatureDfValue)

        # pyworld3 execution
        damage_df, expected_damage_df, co2_damage_price_df = self.model.compute(
            economics_df, temperature_df)

        # store output data
        out_dict = {'expected_damage_df': expected_damage_df,
                    GlossaryCore.DamageDf['var_name']: damage_df,
                    'CO2_damage_price': co2_damage_price_df}

        self.store_sos_outputs_values(out_dict)

    def compute_sos_jacobian(self):
        """ 
        Compute jacobian for each coupling variable 
        gradiant of coupling variable to compute: 
        damage_df
          - GlossaryCore.Damages:
                - temperature_df, GlossaryCore.TempAtmo
                - economics_df, GlossaryCore.GrossOutput
          -GlossaryCore.DamageFractionOutput
                - temperature_df, GlossaryCore.TempAtmo
        """
        ddamage_frac_output_temp_atmo, ddamages_temp_atmo, ddamages_gross_output, dconstraint_CO2_taxes, dconstraint_temp_atmo, dconstraint_economics = self.model.compute_gradient()

        # fill jacobians
        self.set_partial_derivative_for_other_types(
            ('expected_damage_df', GlossaryCore.DamageFractionOutput),
            (GlossaryCore.TemperatureDfValue, GlossaryCore.TempAtmo),  ddamage_frac_output_temp_atmo)

        self.set_partial_derivative_for_other_types(
            ('expected_damage_df', GlossaryCore.Damages),
            (GlossaryCore.TemperatureDfValue, GlossaryCore.TempAtmo),  ddamages_temp_atmo)

        self.set_partial_derivative_for_other_types(
            ('expected_damage_df', GlossaryCore.Damages), (GlossaryCore.EconomicsDfValue, GlossaryCore.GrossOutput),  ddamages_gross_output)

        compute_climate_impact_on_gdp = bool(self.get_sosdisc_inputs('assumptions_dict')['compute_climate_impact_on_gdp']) * 1.0
        self.set_partial_derivative_for_other_types(
            (GlossaryCore.DamageDf['var_name'], GlossaryCore.DamageFractionOutput),
            (GlossaryCore.TemperatureDfValue, GlossaryCore.TempAtmo),
            ddamage_frac_output_temp_atmo * compute_climate_impact_on_gdp)

        self.set_partial_derivative_for_other_types(
            (GlossaryCore.DamageDf['var_name'], GlossaryCore.Damages),
            (GlossaryCore.TemperatureDfValue, GlossaryCore.TempAtmo), ddamages_temp_atmo * compute_climate_impact_on_gdp)

        self.set_partial_derivative_for_other_types(
            (GlossaryCore.DamageDf['var_name'], GlossaryCore.Damages), (GlossaryCore.EconomicsDfValue, GlossaryCore.GrossOutput), ddamages_gross_output * compute_climate_impact_on_gdp)

        self.set_partial_derivative_for_other_types(
            ('CO2_damage_price', 'CO2_damage_price'),
            (GlossaryCore.TemperatureDfValue, GlossaryCore.TempAtmo),  dconstraint_temp_atmo)
        self.set_partial_derivative_for_other_types(
            ('CO2_damage_price', 'CO2_damage_price'), (GlossaryCore.EconomicsDfValue, GlossaryCore.GrossOutput),  dconstraint_economics)

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = [GlossaryCore.Damages, 'CO2 damage price']  # , 'Abatement cost']
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

        if GlossaryCore.Damages in chart_list:

            to_plot = [GlossaryCore.Damages]
            damage_df = deepcopy(self.get_sosdisc_outputs('expected_damage_df'))
            compute_climate_impact_on_gdp = self.get_sosdisc_inputs('assumptions_dict')['compute_climate_impact_on_gdp']
            damage = damage_df[GlossaryCore.Damages]


            years = list(damage_df.index)

            year_start = years[0]
            year_end = years[len(years) - 1]

            min_value, max_value = self.get_greataxisrange(damage)

            chart_name = 'Environmental damage on GDP'
            if not compute_climate_impact_on_gdp:
                chart_name += ' (assumed null in macro-economics)'

            new_chart = TwoAxesInstanciatedChart(GlossaryCore.Years, 'Damage (trill $)',
                                                 [year_start - 5, year_end + 5],
                                                 [min_value, max_value],
                                                 chart_name)

            for key in to_plot:
                visible_line = True

                c_emission = list(damage_df[key])

                new_series = InstanciatedSeries(
                    years, c_emission, key, 'lines', visible_line)

                new_chart.series.append(new_series)

            instanciated_charts.append(new_chart)

        if 'CO2 damage price' in chart_list:

            co2_damage_price_df = deepcopy(
                self.get_sosdisc_outputs('CO2_damage_price'))

            co2_damage_price = co2_damage_price_df['CO2_damage_price']

            years = list(co2_damage_price_df[GlossaryCore.Years].values.tolist())

            year_start = years[0]
            year_end = years[len(years) - 1]

            min_value_1, max_value_1 = self.get_greataxisrange(
                co2_damage_price)

            chart_name = 'CO2 damage price'

            new_chart = TwoAxesInstanciatedChart(GlossaryCore.Years, 'Price ($/tCO2)',
                                                 [year_start - 5, year_end + 5],
                                                 [min_value_1, max_value_1],
                                                 chart_name)

            visible_line = True

            # add CO2 damage price serie
            new_series = InstanciatedSeries(
                years, co2_damage_price.values.tolist(), 'CO2 damage price', 'lines', visible_line)
            new_chart.series.append(new_series)

            # add chart
            instanciated_charts.append(new_chart)

        return instanciated_charts
