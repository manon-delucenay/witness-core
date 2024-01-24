'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/22-2023/11/02 Copyright 2023 Capgemini

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
from sostrades_core.execution_engine.sos_wrapp import SoSWrapp
from sostrades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries, \
    TwoAxesInstanciatedChart
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter


class MountainBiodiversity(SoSWrapp):
    # ontology information
    _ontology_data = {
        'label': 'MountainBiodiversity',
        'type': 'Research',
        'source': 'PIE ISAE-Supaero',
        'validated': '',
        'validated_by': 'No one',
        'last_modification_date': '',
        'last_modification_date': '',
        'category': 'Biodiversity',
        'definition': 'Biodiversity in mountain environment',
        'icon': '??',
        'version': '',
    }
    _maturity = 'Research'
    DESC_IN = { 
               #type = float, dataframe... un peu tout
               #unit
               #visibility = peut être utilisé ailleurs ou pas
               #namespace = pour être appelé ailleurs
        'Pluviometry': {'type': 'float', 'unit': '-'},
        'Temperature': {'type': 'float', 'unit': '-'},
        'LiveStock': {'type': 'float', 'unit': '-'},
        'Tourism': {'type': 'float', 'unit': '-'},
	'PublicPolicies': {'type': 'float', 'unit': '-'},
	'Urbanisation' : {'type': 'float', 'unit': '-'},
    }
    DESC_OUT = {
        'CBI': {'type': 'float', 'unit': '-'},
        #'BHI': {'type': 'float', 'unit': '-', 'visibility': SoSWrapp.SHARED_VISIBILITY, 'namespace': 'ns_ac'}
    }
    
    def init_execution(self):
        #faire ici ce qui doit se faire 1 seule fois pour tout le modèle - genre initialiser un autre système
        MacroEco = MacroeconomicsModel()#quels inputs mettre dedans)
        Population = ... #nom du modèle et ses inputs

    def run(self):
        pluviometry = self.get_sosdisc_inputs('Pluviometry')
        temperature = self.get_sosdisc_inputs('Temperature')
        live = self.get_sosdisc_inputs('LiveStock')
        tourism = self.get_sosdisc_inputs('Tourism')
	policies = self.get_sosdisc_inputs('PublicPolicies')
	urbanisation = self.get_sosdisc_inputs('Urbanisation')
        coef = [...] #COMPLETER
        dict_values = {'CBI': coef * [pluviometry,temperature,live,tourism, policies, urbanisation]}
        # put new field value in data_out
        self.store_sos_outputs_values(dict_values)

    def get_chart_filter_list(self):
        #définir des filtres pour avoir les graph qui nous intéressent
        chart_filters = []

        chart_list = ['y vs x']

        chart_filters.append(ChartFilter(
            'Charts', chart_list, chart_list, 'graphs'))

        return chart_filters

    def get_post_processing_list(self, filters=None):
        #récuperer les input value ET les output - sans utiliser de self. car la classe sera séparé (cherche pas)

        instanciated_charts = []

        # Overload default value with chart filter
        if filters is not None:
            for chart_filter in filters:
                if chart_filter.filter_key == 'graphs':
                    charts_list = chart_filter.selected_values

        if 'y vs x' in charts_list:
            chart_name = 'y vs x'

            y = self.get_sosdisc_outputs('y')
            x = self.get_sosdisc_inputs('x')
            print(y, x)
            new_chart = TwoAxesInstanciatedChart('x (-)', 'y (-)',
                                                 chart_name=chart_name)
            serie = InstanciatedSeries(
                [x], [y], '', 'scatter')

            new_chart.series.append(serie)

            instanciated_charts.append(new_chart)

        return instanciated_charts