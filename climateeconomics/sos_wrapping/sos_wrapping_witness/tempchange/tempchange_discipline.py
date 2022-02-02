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


from climateeconomics.core.core_witness.climateeco_discipline import ClimateEcoDiscipline
from climateeconomics.core.core_witness.tempchange_model import TempChange
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, TwoAxesInstanciatedChart
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
from copy import deepcopy
import pandas as pd
import numpy as np


class TempChangeDiscipline(ClimateEcoDiscipline):
    "     Temperature evolution"
    years = np.arange(2020, 2101)
    DESC_IN = {
        'year_start': {'type': 'int', 'visibility': 'Shared', 'possible_values': years, 'namespace': 'ns_witness'},
        'year_end': {'type': 'int', 'visibility': 'Shared', 'possible_values': years, 'namespace': 'ns_witness'},
        'time_step': {'type': 'int', 'default': 1, 'visibility': 'Shared', 'namespace': 'ns_witness'},
        'init_temp_ocean': {'type': 'float', 'default': 0.02794825, 'user_level': 2},
        'init_temp_atmo': {'type': 'float', 'default': 1.05, 'user_level': 2},
        'eq_temp_impact': {'type': 'float', 'default': 3.1, 'user_level': 3},
        'init_forcing_nonco': {'type': 'float', 'default': 0.83, 'user_level': 2},
        # default is mean value of ssps database
        'hundred_forcing_nonco': {'type': 'float', 'default': 1.1422, 'user_level': 2},
        'climate_upper': {'type': 'float', 'default': 0.1005, 'user_level': 3},
        'transfer_upper': {'type': 'float', 'default': 0.088, 'user_level': 3},
        'transfer_lower': {'type': 'float', 'default': 0.025, 'user_level': 3},
        'forcing_eq_co2': {'type': 'float', 'default': 3.6813, 'user_level': 3},
        'lo_tocean': {'type': 'float', 'default': -1.0, 'user_level': 3},
        'up_tatmo': {'type': 'float', 'default': 12.0, 'user_level': 3},
        'up_tocean': {'type': 'float', 'default': 20.0, 'user_level': 3},
        'carboncycle_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'},
        'alpha': {'type': 'float', 'range': [0., 1.], 'default': 0.5, 'unit': '-',
                  'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'beta': {'type': 'float', 'range': [0., 1.], 'default': 0.5, 'unit': '-',
                 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_witness'},
        'temperature_obj_option': {'type': 'string',
                                   'possible_values': [TempChange.LAST_TEMPERATURE_OBJECTIVE,
                                                       TempChange.INTEGRAL_OBJECTIVE],
                                   'default': TempChange.INTEGRAL_OBJECTIVE,
                                   'visibility': 'Shared', 'namespace': 'ns_witness'},
        'temperature_change_ref': {'type': 'float', 'default': 0.2, 'unit': 'deg', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
                                   'namespace': 'ns_ref', 'user_level': 2},

        'scale_factor_atmo_conc': {'type': 'float', 'default': 1e-2, 'user_level': 2, 'visibility': 'Shared',
                                   'namespace': 'ns_witness'},
    }

    DESC_OUT = {
        'temperature_df': {'type': 'dataframe', 'visibility': 'Shared', 'namespace': 'ns_witness'},
        'temperature_detail_df': {'type': 'dataframe'},
        'temperature_objective': {'type': 'array', 'visibility': 'Shared', 'namespace': 'ns_witness'}}

    _maturity = 'Research'

    # def init_model(self):
    ''' model instantiation '''
    #    return TempChange()

    def init_execution(self):
        in_dict = self.get_sosdisc_inputs()
        self.model = TempChange(in_dict)

    def run(self):
        ''' model execution '''
        # get inputs
        in_dict = self.get_sosdisc_inputs()
#         carboncycle_df = in_dict.pop('carboncycle_df')

        # model execution
        temperature_df, temperature_objective = self.model.compute(in_dict)

        # store output data
        out_dict = {"temperature_detail_df": temperature_df,
                    "temperature_df": temperature_df[['years', 'temp_atmo']],
                    'temperature_objective': temperature_objective}
        self.store_sos_outputs_values(out_dict)

    def compute_sos_jacobian(self):
        """ 
        Compute jacobian for each coupling variable 
        gradient of coupling variable to compute: 
        temperature_df
          - 'forcing':
                - carboncycle_df, 'atmo_conc'
          -'temp_atmo'
                - carboncycle_df, 'atmo_conc'
          - 'temp_ocean',
                - carboncycle_df, 'atmo_conc'
        """
        d_tempatmo_d_atmoconc, d_tempocean_d_atmoconc = self.model.compute_d_temp_atmo()
        d_tempatmoobj_d_temp_atmo = self.model.compute_d_temp_atmo_objective()

        self.set_partial_derivative_for_other_types(
            ('temperature_df', 'temp_atmo'),  ('carboncycle_df', 'atmo_conc'), d_tempatmo_d_atmoconc,)

        # dtao => derivative temp atmo obj
        # dac => derivative atmo conc
        # dta => derivative temp atmo
        # dtao/dac = dtao/dta * dta/dac
        self.set_partial_derivative_for_other_types(
            ('temperature_objective', ),  ('carboncycle_df', 'atmo_conc'),  d_tempatmoobj_d_temp_atmo.dot(d_tempatmo_d_atmoconc),)

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = ['temperature evolution']
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

        if 'temperature evolution' in chart_list:

            to_plot = ['temp_atmo', 'temp_ocean']
            temperature_df = deepcopy(
                self.get_sosdisc_outputs('temperature_detail_df'))

            legend = {'temp_atmo': 'atmosphere temperature',
                      'temp_ocean': 'ocean temperature'}

            years = list(temperature_df.index)

            year_start = years[0]
            year_end = years[len(years) - 1]

            max_values = {}
            min_values = {}
            for key in to_plot:
                min_values[key], max_values[key] = self.get_greataxisrange(
                    temperature_df[to_plot])

            min_value = min(min_values.values())
            max_value = max(max_values.values())

            chart_name = 'Temperature evolution over the years'

            new_chart = TwoAxesInstanciatedChart('years', 'temperature evolution (degrees Celsius above preindustrial)',
                                                 [year_start - 5, year_end + 5], [
                                                     min_value, max_value],
                                                 chart_name)

            for key in to_plot:
                visible_line = True

                ordonate_data = list(temperature_df[key])

                new_series = InstanciatedSeries(
                    years, ordonate_data, legend[key], 'lines', visible_line)

                new_chart.series.append(new_series)

            instanciated_charts.append(new_chart)

        return instanciated_charts