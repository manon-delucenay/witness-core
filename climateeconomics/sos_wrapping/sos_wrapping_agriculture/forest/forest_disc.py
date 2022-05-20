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
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import InstanciatedSeries,\
    TwoAxesInstanciatedChart
from climateeconomics.core.core_forest.forest_v2 import Forest
from energy_models.core.stream_type.energy_models.biomass_dry import BiomassDry
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from copy import deepcopy
from sos_trades_core.tools.post_processing.plotly_native_charts.instantiated_plotly_native_chart import \
    InstantiatedPlotlyNativeChart


class ForestDiscipline(ClimateEcoDiscipline):
    ''' Forest discipline
    '''

    # ontology information
    _ontology_data = {
        'label': 'Forest',
        'type': '',
        'source': '',
        'validated': '',
        'validated_by': '',
        'last_modification_date': '',
        'category': '',
        'definition': '',
        'icon': 'fas fa-tree fa-fw',
        'version': '',
    }
    AGRI_CAPITAL_TECHNO_LIST = ['Forest']
    biomass_cal_val = BiomassDry.data_energy_dict[
        'calorific_value']
    default_year_start = 2020
    default_year_end = 2050

    deforestation_limit = 1000
    initial_emissions = 3.21

    construction_delay = 3  # years, time for wood to dry

    # available planted forests in 2020: 294 Mha (worldbioenergy.org)

    # reference:
    # https://qtimber.daf.qld.gov.au/guides/wood-density-and-hardness
    wood_density = 600.0  # kg/m3
    residues_density = 200.0  # kg/m3

    # reference :
    # https://www.eubia.org/cms/wiki-biomass/biomass-resources/challenges-related-to-biomass/recovery-of-forest-residues/
    # average of 155 and 310 divided by 5
    residue_density_m3_per_ha = 46.5
    # average of 360 and 600 divided by 5
    wood_density_m3_per_ha = 96

    # in litterature, average price of residue is 30-50euro/t
    # wood price is 100-200euro/t => 26% between
    wood_residue_price_percent_dif = 0.34

    # 1,62% of managed wood is used for energy purpose
    # (3% of global forest is used for energy purpose and
    # 54% of global forest are managed forests)
    wood_percentage_for_energy = 0.48
    residue_percentage_for_energy = 0.48

    density_per_ha = residue_density_m3_per_ha + \
        wood_density_m3_per_ha

    wood_percentage = wood_density_m3_per_ha / density_per_ha
    residue_percentage = residue_density_m3_per_ha / density_per_ha

    mean_density = wood_percentage * wood_density + \
        residue_percentage * residues_density

    # reference :
    # https://www.eubia.org/cms/wiki-biomass/biomass-resources/challenges-related-to-biomass/recovery-of-forest-residues/
    years_between_harvest = 25

    recycle_part = 0.52  # 52%
#     mean_calorific_value = BiomassDryTechnoDiscipline.data_energy_dict[
#         'calorific_value']

    wood_techno_dict = {'maturity': 5,
                        'wood_residues_moisture': 0.35,  # 35% moisture content
                        'wood_residue_colorific_value': 4.356,
                        # teagasc : 235euro/ha/year for planting 5% and spot spraying and manual cleaning
                        # +  chipping + off_road transport 8 euro/Mwh (www.eubia.org )
                        # for wood + residues
                        'Opex_percentage': 0.045,
                        # Capex init: 12000 $/ha to buy the land (CCUS-report_V1.30)
                        # + 2564.128 euro/ha (ground preparation, planting) (www.teagasc.ie)
                        # 1USD = 0,87360 euro in 2019
                        'managed_wood_price_per_ha': 13047,
                        'Price_per_ha_unit': '$/ha',
                        'full_load_hours': 8760.0,
                        'euro_dollar': 1.1447,  # in 2019, date of the paper
                        'percentage_production': 0.52,
                        'residue_density_percentage': residue_percentage,
                        'non_residue_density_percentage': wood_percentage,
                        'density_per_ha': density_per_ha,
                        'wood_percentage_for_energy': wood_percentage_for_energy,
                        'residue_percentage_for_energy': residue_percentage_for_energy,
                        'density': mean_density,
                        'wood_density': wood_density,
                        'residues_density': residues_density,
                        'density_per_ha_unit': 'm^3/ha',
                        'techno_evo_eff': 'no',  # yes or no
                        'years_between_harvest': years_between_harvest,
                        'wood_residue_price_percent_dif': wood_residue_price_percent_dif,
                        'recycle_part': recycle_part,
                        'construction_delay': construction_delay,
                        'WACC': 0.07,
                        # CO2 from production from tractor is taken
                        # into account into the energy net factor
                        # land CO2 absorption is computed in land_emission with
                        # the CO2_per_ha parameter
                        'CO2_from_production': 0.0,
                        'CO2_from_production_unit': 'kg/kg'}

# invest: 0.19 Mha are planted each year at 13047.328euro/ha, and 28% is
    # the share of wood (not residue)
    invest_before_year_start = pd.DataFrame(
        {'past_years': np.arange(-construction_delay, 0), 'investment': [1.135081, 1.135081, 1.135081]})
    # www.fao.org : forest under long-term management plans = 2.05 Billion Ha
    # 31% of All forests is used for production : 0.31 * 4.06 = 1.25
    # 92% of the production come from managed wood. 8% from unmanaged wood
    mw_initial_production = round(1.25 * 0.92 *
                                  density_per_ha * mean_density * biomass_cal_val /
                                  years_between_harvest / (1 - recycle_part), 6)  # in Twh
    mw_initial_surface = round(1.25 * 0.92, 6)

    # protected forest are 21% of total forest
    # https://research.wri.org/gfr/forest-designation-indicators/protected-forests
    initial_protected_forest_surface = 4 * 0.21
    initial_unsused_forest_surface = 4 - 1.25 - initial_protected_forest_surface

    # reforestation costs: 10k$/ha of land and 3800$/ha to plant trees

    DESC_IN = {
        'year_start': ClimateEcoDiscipline.YEAR_START_DESC_IN,
        'year_end': ClimateEcoDiscipline.YEAR_END_DESC_IN,
        'time_step': ClimateEcoDiscipline.TIMESTEP_DESC_IN,
        Forest.DEFORESTATION_INVESTMENT: {'type': 'dataframe', 'unit': 'G$',
                                          'dataframe_descriptor': {'years': ('float', None, False),
                                                                   'investment': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False,
                                          'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        Forest.DEFORESTATION_COST_PER_HA: {'type': 'float', 'unit': '$/ha',  'default': 8000,
                                           'namespace': 'ns_forest'},
        Forest.LIMIT_DEFORESTATION_SURFACE: {'type': 'float', 'unit': 'Mha',  'default': deforestation_limit,
                                             'namespace': 'ns_forest', },
        Forest.INITIAL_CO2_EMISSIONS: {'type': 'float', 'unit': 'GtCO2',  'default': initial_emissions,
                                       'namespace': 'ns_forest', },
        Forest.CO2_PER_HA: {'type': 'float', 'unit': 'kgCO2/ha/year',  'default': 4000,
                            'namespace': 'ns_forest'},
        Forest.REFORESTATION_COST_PER_HA: {'type': 'float', 'unit': '$/ha',  'default': 13800,
                                           'namespace': 'ns_forest'},
        Forest.REFORESTATION_INVESTMENT: {'type': 'dataframe', 'unit': 'G$',
                                          'dataframe_descriptor': {'years': ('float', None, False),
                                                                   'forest_investment': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False,
                                          'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_invest'},
        Forest.WOOD_TECHNO_DICT: {'type': 'dict', 'unit': '-',  'default': wood_techno_dict,
                                  'namespace': 'ns_forest'},
        Forest.MW_INITIAL_PROD: {'type': 'float', 'unit': 'TWh',  'default': mw_initial_production,
                                 'namespace': 'ns_forest'},
        Forest.MW_INITIAL_SURFACE: {'type': 'float', 'unit': 'Gha',  'default': mw_initial_surface,
                                    'namespace': 'ns_forest'},
        Forest.MW_INVEST_BEFORE_YEAR_START: {'type': 'dataframe', 'unit': 'G$',
                                             'dataframe_descriptor': {'past_years': ('float', None, False),
                                                                      'investment': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False,
                                             'default': invest_before_year_start,
                                             'namespace': 'ns_forest'},
        Forest.MW_INVESTMENT: {'type': 'dataframe', 'unit': 'G$',
                               'dataframe_descriptor': {'years': ('float', None, False),
                                                        'investment': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False,
                               'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        Forest.TRANSPORT_COST: {'type': 'dataframe', 'unit': '$/t', 'namespace': 'ns_witness', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
                                'dataframe_descriptor': {'years': ('float', None, False),
                                                         'transport': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False},
        Forest.MARGIN: {'type': 'dataframe', 'unit': '%', 'namespace': 'ns_witness', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
                                'dataframe_descriptor': {'years': ('float', None, False),
                                                         'margin': ('float', [0, 1e9], True)}, 'dataframe_edition_locked': False},
        Forest.UNMANAGED_FOREST: {'type': 'float', 'unit': 'Gha',   'default': initial_unsused_forest_surface,
                                  'namespace': 'ns_forest'},
        Forest.PROTECTED_FOREST: {'type': 'float', 'unit': 'Gha',   'default': initial_protected_forest_surface,
                                  'namespace': 'ns_forest'},
        'scaling_factor_techno_consumption': {'type': 'float', 'default': 1e3, 'unit': '-', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_public', 'user_level': 2},
        'scaling_factor_techno_production': {'type': 'float', 'default': 1e3, 'unit': '-', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_public', 'user_level': 2},
    }

    DESC_OUT = {
        Forest.CO2_EMITTED_DETAIL_DF: {
            'type': 'dataframe', 'unit': 'GtCO2', 'namespace': 'ns_forest'},
        Forest.FOREST_DETAIL_SURFACE_DF: {
            'type': 'dataframe', 'unit': 'Gha'},
        Forest.FOREST_SURFACE_DF: {
            'type': 'dataframe', 'unit': 'Gha', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
            'namespace': 'ns_witness'},
        Forest.CO2_EMITTED_FOREST_DF: {
            'type': 'dataframe', 'unit': 'GtCO2', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
            'namespace': 'ns_forest'},
        'CO2_land_emission_df': {
            'type': 'dataframe', 'unit': 'GtCO2', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
            'namespace': 'ns_forest'},
        Forest.BIOMASS_DRY_DF: {
            'type': 'dataframe', 'unit': '-', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
            'namespace': 'ns_witness'},
        Forest.MW_DF: {
            'type': 'dataframe', 'unit': 'Gha', 'namespace': 'ns_forest'},
        Forest.BIOMASS_DRY_DETAIL_DF: {
            'type': 'dataframe', 'unit': '-', 'namespace': 'ns_forest'},

        'techno_production': {
            'type': 'dataframe', 'unit': 'TWh or Mt', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        'techno_prices': {
            'type': 'dataframe', 'unit': '$/MWh', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        'techno_consumption': {
            'type': 'dataframe', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest', 'unit': 'TWh or Mt'},
        'techno_consumption_woratio': {
            'type': 'dataframe', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest', 'unit': 'TWh or Mt'},
        'land_use_required': {
            'type': 'dataframe', 'unit': 'Gha', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        'CO2_emissions': {
            'type': 'dataframe', 'unit': 'kg/kWh', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY,
            'namespace': 'ns_forest'},
        'techno_capital': {
            'type': 'dataframe', 'unit': 'G$', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
        'non_use_capital': {
            'type': 'dataframe', 'unit': 'G$', 'visibility': ClimateEcoDiscipline.SHARED_VISIBILITY, 'namespace': 'ns_forest'},
    }

    FOREST_CHARTS = 'Forest chart'

    def init_execution(self):

        param = self.get_sosdisc_inputs()

        self.forest_model = Forest(param)

    def run(self):

        #-- get inputs
        #         inputs = list(self.DESC_IN.keys())
        #         inp_dict = self.get_sosdisc_inputs(inputs, in_dict=True)

        #-- compute
        inputs_dict = self.get_sosdisc_inputs()
        self.forest_model.compute(inputs_dict)
        # Scale production TWh -> PWh
        techno_production = self.forest_model.techno_production[[
            'years', 'biomass_dry (TWh)']]
        for column in techno_production.columns:
            if column == 'years':
                continue
            techno_production[column] = techno_production[column].values / \
                inputs_dict['scaling_factor_techno_production']
        # Scale production Mt -> Gt
        techno_consumption = deepcopy(self.forest_model.techno_consumption)
        techno_consumption_woratio = deepcopy(
            self.forest_model.techno_consumption_woratio)
        for column in techno_consumption.columns:
            if column == 'years':
                continue
            techno_consumption[column] = techno_consumption[column].values / \
                inputs_dict['scaling_factor_techno_consumption']
            techno_consumption_woratio[column] = techno_consumption_woratio[column].values / \
                inputs_dict['scaling_factor_techno_consumption']

        outputs_dict = {
            Forest.CO2_EMITTED_DETAIL_DF: self.forest_model.CO2_emitted_df,
            Forest.FOREST_DETAIL_SURFACE_DF: self.forest_model.forest_surface_df,
            Forest.FOREST_SURFACE_DF: self.forest_model.forest_surface_df[['years', 'global_forest_surface', 'forest_constraint_evolution']],
            Forest.CO2_EMITTED_FOREST_DF: self.forest_model.CO2_emitted_df[['years', 'emitted_CO2_evol_cumulative']],
            'CO2_land_emission_df': self.forest_model.CO2_emitted_df[['years', 'emitted_CO2_evol_cumulative']],
            'managed_wood_df': self.forest_model.managed_wood_df,
            #'unmanaged_wood_df': self.forest_model.unmanaged_wood_df,
            'biomass_dry_detail_df': self.forest_model.biomass_dry_df,
            'biomass_dry_df': self.forest_model.biomass_dry_df[['years', 'price_per_MWh', 'biomass_dry_for_energy (Mt)']],

            'techno_production': techno_production,
            'techno_prices': self.forest_model.techno_prices,
            'techno_consumption': techno_consumption,
            'techno_consumption_woratio': techno_consumption_woratio,
            'land_use_required': self.forest_model.land_use_required,
            'CO2_emissions': self.forest_model.CO2_emissions,
            'non_use_capital': self.forest_model.lost_capital,
            'techno_capital': self.forest_model.techno_capital,
        }
        #-- store outputs
        self.store_sos_outputs_values(outputs_dict)

    def compute_sos_jacobian(self):
        """
        Compute jacobian for each coupling variable
        """
        inputs_dict = self.get_sosdisc_inputs()
        self.forest_model.compute(inputs_dict)
        wood_techno_dict = inputs_dict['wood_techno_dict']
        mw_price_per_ha = wood_techno_dict['managed_wood_price_per_ha']
        deforest_price_per_ha = inputs_dict['deforestation_cost_per_ha']
        wood_percentage_for_energy = wood_techno_dict['wood_percentage_for_energy']
        residue_percentage_for_energy = wood_techno_dict['residue_percentage_for_energy']
        residue_percentage = wood_techno_dict['residue_density_percentage']
        wood_percentage = wood_techno_dict['non_residue_density_percentage']
        scaling_factor_techno_production = inputs_dict['scaling_factor_techno_production']
        scaling_factor_techno_consumption = inputs_dict['scaling_factor_techno_consumption']
        CO2_from_production = inputs_dict['wood_techno_dict']['CO2_from_production']
        high_calorific_value = BiomassDry.data_energy_dict['high_calorific_value']
        # kwh/kg
        calorific_value = BiomassDry.data_energy_dict['calorific_value']

        # gradient for deforestation rate
        d_deforestation_surface_d_deforestation_investment = self.forest_model.d_deforestation_surface_d_deforestation_invest()
        d_cum_deforestation_d_deforestation_invest = self.forest_model.d_cum(
            d_deforestation_surface_d_deforestation_investment)
        d_forest_surface_d_invest = self.forest_model.d_forestation_surface_d_invest()
        d_cum_forest_surface_d_invest = self.forest_model.d_cum(
            d_forest_surface_d_invest)
        d_mw_surface_d_invest = self.forest_model.d_wood_techno_surface_d_invest(
            mw_price_per_ha)
        d_cum_mw_surface_d_invest = self.forest_model.d_cum_managed_forest(
            d_mw_surface_d_invest)

        # forest surface vs deforestation grad
        self.set_partial_derivative_for_other_types((Forest.FOREST_SURFACE_DF, 'global_forest_surface'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'), d_cum_deforestation_d_deforestation_invest)
        # forest surface vs forest invest
        self.set_partial_derivative_for_other_types((Forest.FOREST_SURFACE_DF, 'global_forest_surface'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), d_cum_forest_surface_d_invest)

        self.set_partial_derivative_for_other_types((Forest.FOREST_SURFACE_DF, 'global_forest_surface'), (
            'managed_wood_investment', 'investment'), d_cum_mw_surface_d_invest)

        self.set_partial_derivative_for_other_types((Forest.FOREST_SURFACE_DF, 'forest_constraint_evolution'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'), d_cum_deforestation_d_deforestation_invest)
        # forest surface vs forest invest
        self.set_partial_derivative_for_other_types((Forest.FOREST_SURFACE_DF, 'forest_constraint_evolution'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), d_cum_forest_surface_d_invest)

        # total capital vs reforestation investment grad
        dcapitaltotal_dinvest = self.forest_model.d_capital_total_d_invest()
        self.set_partial_derivative_for_other_types(('techno_capital', 'Forest'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), dcapitaltotal_dinvest)

        # lost capital vs reforestation investment grad
        dlostcapital_dinvest = self.forest_model.d_lostcapitald_invest(
            d_forest_surface_d_invest)
        self.set_partial_derivative_for_other_types(('non_use_capital', 'Forest'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), dlostcapital_dinvest)

        # land use required

        # forest surface vs managed wood invest
        self.set_partial_derivative_for_other_types(('land_use_required', 'Forest (Gha)'), (
            'managed_wood_investment', 'investment'), d_cum_mw_surface_d_invest)

        d_land_use_d_deforest_invest = self.forest_model.d_mw_surf_d_deforest_invest()
        self.set_partial_derivative_for_other_types(('land_use_required', 'Forest (Gha)'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'), d_land_use_d_deforest_invest)

        # d_CO2 d deforestation
        d_CO2_emitted_d_deforestation_surface = self.forest_model.d_CO2_emitted(
            d_deforestation_surface_d_deforestation_investment)
        d_cum_CO2_emitted_d_deforestation_surface = self.forest_model.d_cum(
            d_CO2_emitted_d_deforestation_surface)
        self.set_partial_derivative_for_other_types((Forest.CO2_EMITTED_FOREST_DF, 'emitted_CO2_evol_cumulative'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'),
            d_cum_CO2_emitted_d_deforestation_surface)
        self.set_partial_derivative_for_other_types(('CO2_land_emission_df', 'emitted_CO2_evol_cumulative'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'),
            d_cum_CO2_emitted_d_deforestation_surface)

        # d_CO2 d invest reforestation
        d_cum_CO2_emitted_d_invest_ref = self.forest_model.d_CO2_emitted(
            d_cum_forest_surface_d_invest)
        self.set_partial_derivative_for_other_types(('CO2_land_emission_df', 'emitted_CO2_evol_cumulative'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), d_cum_CO2_emitted_d_invest_ref)
        self.set_partial_derivative_for_other_types((Forest.CO2_EMITTED_FOREST_DF, 'emitted_CO2_evol_cumulative'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), d_cum_CO2_emitted_d_invest_ref)

        # d techno_production managed wood invest
        d_biomass_residues_d_mw_invest = self.forest_model.d_biomass_prod_d_invest(
            d_cum_mw_surface_d_invest, residue_percentage, residue_percentage_for_energy)
        d_biomass_wood_d_mw_invest = self.forest_model.d_biomass_prod_d_invest(
            d_cum_mw_surface_d_invest, wood_percentage, wood_percentage_for_energy)
        self.set_partial_derivative_for_other_types(('techno_production', 'biomass_dry (TWh)'), ('managed_wood_investment', 'investment'),
                                                    (d_biomass_residues_d_mw_invest + d_biomass_wood_d_mw_invest) * calorific_value / scaling_factor_techno_production)
        self.set_partial_derivative_for_other_types(('techno_consumption', 'CO2_resource (Mt)'), ('managed_wood_investment', 'investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    (d_biomass_residues_d_mw_invest +
                                                     d_biomass_wood_d_mw_invest)
                                                    * calorific_value / scaling_factor_techno_consumption)
        self.set_partial_derivative_for_other_types(('techno_consumption_woratio', 'CO2_resource (Mt)'), ('managed_wood_investment', 'investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    (d_biomass_residues_d_mw_invest +
                                                     d_biomass_wood_d_mw_invest)
                                                    * calorific_value / scaling_factor_techno_consumption)
        # d biomass prod d deforestation invest
        d_biomass_prod_d_deforestation = self.forest_model.d_biomass_prod_d_deforestation_invest(
            d_deforestation_surface_d_deforestation_investment)
        d_biomass_residues_d_deforest_invest = self.forest_model.d_biomass_prod_d_invest(
            d_land_use_d_deforest_invest, residue_percentage, residue_percentage_for_energy)
        d_biomass_wood_d_deforest_invest = self.forest_model.d_biomass_prod_d_invest(
            d_land_use_d_deforest_invest, wood_percentage, wood_percentage_for_energy)
        B = d_biomass_residues_d_deforest_invest + d_biomass_wood_d_deforest_invest
        self.set_partial_derivative_for_other_types(('techno_production', 'biomass_dry (TWh)'), (Forest.DEFORESTATION_INVESTMENT, 'investment'),
                                                    (d_biomass_prod_d_deforestation + B) * calorific_value / scaling_factor_techno_production)
        self.set_partial_derivative_for_other_types(('techno_consumption', 'CO2_resource (Mt)'), (Forest.DEFORESTATION_INVESTMENT, 'investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    (d_biomass_prod_d_deforestation + B) * calorific_value / scaling_factor_techno_consumption)
        self.set_partial_derivative_for_other_types(('techno_consumption_woratio', 'CO2_resource (Mt)'), (Forest.DEFORESTATION_INVESTMENT, 'investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    (d_biomass_prod_d_deforestation + B) * calorific_value / scaling_factor_techno_consumption)
        # d biomass price d MW invest
        d_biomass_price_d_mw_invest = self.forest_model.d_biomass_price_d_invest_mw(
            mw_price_per_ha)
        self.set_partial_derivative_for_other_types(('techno_prices', 'Forest'), (
            'managed_wood_investment', 'investment'), d_biomass_price_d_mw_invest)
        self.set_partial_derivative_for_other_types(('techno_prices', 'Forest_wotaxes'), (
            'managed_wood_investment', 'investment'), d_biomass_price_d_mw_invest)

        # d biomass price d deforest invest
        d_biomass_price_d_invest_deforest = self.forest_model.d_biomass_price_d_invest_deforest_limit(
            d_biomass_prod_d_deforestation, B)
        self.set_partial_derivative_for_other_types(('techno_prices', 'Forest'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'), d_biomass_price_d_invest_deforest)
        self.set_partial_derivative_for_other_types(('techno_prices', 'Forest_wotaxes'), (
            Forest.DEFORESTATION_INVESTMENT, 'investment'),
            d_biomass_price_d_invest_deforest)

        # d managed_wood_surface d reforestation invest
        d_mw_surf_d_reforest_invest = self.forest_model.d_managed_wood_surf_d_invest_reforestation(
            d_cum_forest_surface_d_invest)
        d_wood_prod_d_forest_invest = self.forest_model.d_biomass_prod_d_invest_reforestation(
            d_mw_surf_d_reforest_invest, wood_percentage, wood_percentage_for_energy)
        d_residue_prod_d_forest_invest = self.forest_model.d_biomass_prod_d_invest_reforestation(
            d_mw_surf_d_reforest_invest, residue_percentage,
            wood_percentage_for_energy)
        d_biomass_prod_d_reforest_invest = d_wood_prod_d_forest_invest + \
            d_residue_prod_d_forest_invest

        d_land_use_d_deforest_invest = self.forest_model.d_mw_surf_d_deforest_invest()
        self.set_partial_derivative_for_other_types(('land_use_required', 'Forest (Gha)'), (
            Forest.REFORESTATION_INVESTMENT, 'forest_investment'), d_mw_surf_d_reforest_invest)

        self.set_partial_derivative_for_other_types(('techno_production', 'biomass_dry (TWh)'), (Forest.REFORESTATION_INVESTMENT, 'forest_investment'),
                                                    d_biomass_prod_d_reforest_invest * calorific_value / scaling_factor_techno_production)
        self.set_partial_derivative_for_other_types(('techno_consumption', 'CO2_resource (Mt)'), (Forest.REFORESTATION_INVESTMENT, 'forest_investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    d_biomass_prod_d_reforest_invest * calorific_value / scaling_factor_techno_consumption)
        self.set_partial_derivative_for_other_types(('techno_consumption_woratio', 'CO2_resource (Mt)'), (Forest.REFORESTATION_INVESTMENT, 'forest_investment'),
                                                    -CO2_from_production / high_calorific_value *
                                                    d_biomass_prod_d_reforest_invest * calorific_value / scaling_factor_techno_consumption)

    def get_chart_filter_list(self):

        # For the outputs, making a graph for tco vs year for each range and for specific
        # value of ToT with a shift of five year between then

        chart_filters = []

        chart_list = [ForestDiscipline.FOREST_CHARTS]

        # First filter to deal with the view : program or actor
        chart_filters.append(ChartFilter(
            'Charts filter', chart_list, chart_list, 'charts'))

        return chart_filters

    def get_post_processing_list(self, chart_filters=None):
        '''
        For the outputs, making a graph for tco vs year for each range and for specific
        value of ToT with a shift of five year between then
        '''
        instanciated_charts = []

        # Overload default value with chart filter
        if chart_filters is not None:
            for chart_filter in chart_filters:
                if chart_filter.filter_key == 'charts':
                    chart_list = chart_filter.selected_values

        forest_surface_df = self.get_sosdisc_outputs(
            Forest.FOREST_DETAIL_SURFACE_DF)

        managed_wood_df = self.get_sosdisc_outputs(
            'managed_wood_df')

        if ForestDiscipline.FOREST_CHARTS in chart_list:

            years = forest_surface_df['years'].values.tolist()
            # values are *1000 to convert from Gha to Mha
            delta_reforestation = forest_surface_df['delta_reforestation_surface'].values * 1000
            reforestation = forest_surface_df['reforestation_surface'].values * 1000

            delta_deforestation = forest_surface_df['delta_deforestation_surface'].values * 1000
            deforestation = forest_surface_df['deforestation_surface'].values * 1000

            delta_managed_wood_surface = managed_wood_df['delta_surface'].values * 1000
            managed_wood_surface = managed_wood_df['cumulative_surface'].values * 1000

            delta_global = forest_surface_df['delta_global_forest_surface'].values * 1000
            global_surface = forest_surface_df['global_forest_surface'].values * 1000

            unmanaged_forest = forest_surface_df['unmanaged_forest'].values * 1000
            protected_forest = forest_surface_df['protected_forest_surface'].values * 1000

            # forest evolution year by year chart
            new_chart = TwoAxesInstanciatedChart('years', 'Yearly delta of forest surface evolution [Mha / year]',
                                                 chart_name='Yearly delta of forest surface evolution', stacked_bar=True)

            deforested_series = InstanciatedSeries(
                years, delta_deforestation.tolist(), 'Deforestation', 'bar')
            forested_series = InstanciatedSeries(
                years, delta_reforestation.tolist(), 'Reforestation', 'bar')
            total_series = InstanciatedSeries(
                years, delta_global.tolist(), 'Global forest surface', InstanciatedSeries.LINES_DISPLAY)
            managed_wood_series = InstanciatedSeries(
                years, delta_managed_wood_surface.tolist(), 'Managed wood', 'bar')

            new_chart.add_series(deforested_series)
            new_chart.add_series(total_series)
            new_chart.add_series(forested_series)
            # new_chart.add_series(managed_wood_series)

            instanciated_charts.append(new_chart)

            # forest cumulative evolution chart
            new_chart = TwoAxesInstanciatedChart('years', 'Forest surface evolution [Mha]',
                                                 chart_name='Global forest surface evolution', stacked_bar=True)

            deforested_series = InstanciatedSeries(
                years, deforestation.tolist(), 'Deforested surface', 'bar')
            forested_series = InstanciatedSeries(
                years, reforestation.tolist(), 'Reforested surface', 'bar')
            total_series = InstanciatedSeries(
                years, global_surface.tolist(), 'Forest surface evolution', InstanciatedSeries.LINES_DISPLAY)
            managed_wood_series = InstanciatedSeries(
                years, managed_wood_surface.tolist(), 'Managed wood', 'bar')
            unmanaged_forest_series = InstanciatedSeries(
                years, unmanaged_forest.tolist(), 'Unmanaged forest', 'bar')
            protected_forest_series = InstanciatedSeries(
                years, protected_forest.tolist(), 'Protected forest', 'bar')

            new_chart.add_series(unmanaged_forest_series)
            new_chart.add_series(total_series)
            # new_chart.add_series(forested_series)
            new_chart.add_series(managed_wood_series)
            new_chart.add_series(protected_forest_series)

            instanciated_charts.append(new_chart)

            # CO2 graph

            CO2_emissions_df = self.get_sosdisc_outputs(
                'CO2_emissions_detail_df')

            delta_reforestation = CO2_emissions_df['delta_CO2_reforestation'].values
            reforestation = CO2_emissions_df['CO2_reforestation'].values

            delta_deforestation = CO2_emissions_df['delta_CO2_deforestation'].values
            deforestation = CO2_emissions_df['CO2_deforestation'].values

            delta_managed_wood_surface = managed_wood_df['delta_CO2_emitted'].values
            managed_wood_surface = managed_wood_df['CO2_emitted'].values

            delta_global = CO2_emissions_df['delta_CO2_emitted'].values
            global_surface = CO2_emissions_df['emitted_CO2_evol_cumulative'].values

            new_chart = TwoAxesInstanciatedChart('years', 'CO2 emission & capture [GtCO2 / year]',
                                                 chart_name='Yearly forest delta CO2 emissions', stacked_bar=True)

            CO2_deforestation_series = InstanciatedSeries(
                years, delta_deforestation.tolist(), 'Deforestation emissions', InstanciatedSeries.BAR_DISPLAY)
            CO2_reforestation_series = InstanciatedSeries(
                years, delta_reforestation.tolist(), 'Reforestation emissions', InstanciatedSeries.BAR_DISPLAY)
            CO2_total_series = InstanciatedSeries(
                years, delta_global.tolist(), 'Global CO2 balance', InstanciatedSeries.LINES_DISPLAY)
            CO2_managed_wood_series = InstanciatedSeries(
                years, delta_managed_wood_surface.tolist(), 'Managed wood emissions', InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(CO2_deforestation_series)
            new_chart.add_series(CO2_total_series)
            new_chart.add_series(CO2_reforestation_series)
            # new_chart.add_series(CO2_managed_wood_series)

            instanciated_charts.append(new_chart)

            # in Gt
            new_chart = TwoAxesInstanciatedChart('years', 'CO2 emission & capture [GtCO2]',
                                                 chart_name='Forest CO2 emissions', stacked_bar=True)
            CO2_deforestation_series = InstanciatedSeries(
                years, deforestation.tolist(), 'Deforestation emissions', InstanciatedSeries.BAR_DISPLAY)
            CO2_reforestation_series = InstanciatedSeries(
                years, reforestation.tolist(), 'Reforestation emissions', InstanciatedSeries.BAR_DISPLAY)
            CO2_total_series = InstanciatedSeries(
                years, global_surface.tolist(), 'Global CO2 balance', InstanciatedSeries.LINES_DISPLAY)
            CO2_managed_wood_series = InstanciatedSeries(
                years, managed_wood_surface.tolist(), 'Managed wood emissions', InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(CO2_deforestation_series)
            new_chart.add_series(CO2_total_series)
            new_chart.add_series(CO2_reforestation_series)
            instanciated_charts.append(new_chart)

            # biomass chart
            biomass_dry_df = self.get_sosdisc_outputs(
                'biomass_dry_detail_df')

            # chart biomass dry for energy production
            new_chart = TwoAxesInstanciatedChart('years', 'biomass dry [Mt]',
                                                 chart_name='Break down of biomass dry production for energy', stacked_bar=True)
            mw_residues_energy = managed_wood_df[
                'residues_production_for_energy (Mt)']
            mw_wood_energy = managed_wood_df['wood_production_for_energy (Mt)']
            biomass_dry_energy = biomass_dry_df['biomass_dry_for_energy (Mt)']
            deforestation_energy = biomass_dry_df['deforestation_for_energy']

            mn_residues_series = InstanciatedSeries(
                years, mw_residues_energy.tolist(), 'Residues from managed wood', InstanciatedSeries.BAR_DISPLAY)
            mn_wood_series = InstanciatedSeries(
                years, mw_wood_energy.tolist(), 'Wood from managed wood', InstanciatedSeries.BAR_DISPLAY)
            deforestation_series = InstanciatedSeries(
                years, deforestation_energy.tolist(), 'Biomass from deforestation', InstanciatedSeries.BAR_DISPLAY)
            biomass_dry_energy_series = InstanciatedSeries(
                years, biomass_dry_energy.tolist(), 'Total biomass dry produced', InstanciatedSeries.LINES_DISPLAY)

            new_chart.add_series(mn_residues_series)
            new_chart.add_series(mn_wood_series)
            new_chart.add_series(deforestation_series)
            new_chart.add_series(biomass_dry_energy_series)
            instanciated_charts.append(new_chart)

            # chart biomass dry for energy production
            new_chart = TwoAxesInstanciatedChart('years', 'Biomass dry [TWh]',
                                                 chart_name='Break down of biomass dry production for energy', stacked_bar=True)
            mw_residues_energy_twh = managed_wood_df[
                'residues_production_for_energy (Mt)'] * ForestDiscipline.biomass_cal_val
            mw_wood_energy_twh = managed_wood_df['wood_production_for_energy (Mt)'] * \
                ForestDiscipline.biomass_cal_val
            biomass_dry_energy_twh = biomass_dry_df['biomass_dry_for_energy (Mt)'] * \
                ForestDiscipline.biomass_cal_val
            deforestation_energy_twh = biomass_dry_df['deforestation_for_energy'] * \
                ForestDiscipline.biomass_cal_val

            mn_residues_series = InstanciatedSeries(
                years, mw_residues_energy_twh.tolist(), 'Residues from managed wood', InstanciatedSeries.BAR_DISPLAY)
            mn_wood_series = InstanciatedSeries(
                years, mw_wood_energy_twh.tolist(), 'Wood from managed wood', InstanciatedSeries.BAR_DISPLAY)
            deforestation_series = InstanciatedSeries(
                years, deforestation_energy_twh.tolist(), 'Biomass from deforestation', InstanciatedSeries.BAR_DISPLAY)
            biomass_dry_energy_series = InstanciatedSeries(
                years, biomass_dry_energy_twh.tolist(), 'Total biomass dry produced', InstanciatedSeries.LINES_DISPLAY)

            new_chart.add_series(mn_residues_series)
            new_chart.add_series(mn_wood_series)
            new_chart.add_series(deforestation_series)
            new_chart.add_series(biomass_dry_energy_series)
            instanciated_charts.append(new_chart)

            # chart total biomass dry production
            new_chart = TwoAxesInstanciatedChart('years', 'biomass dry [Mt]',
                                                 chart_name='Break down of biomass dry production', stacked_bar=True)
            residues_industry = managed_wood_df[
                'residues_production_for_industry (Mt)'].values
            wood_industry = managed_wood_df['wood_production_for_industry (Mt)'].values
            deforestation_industry = biomass_dry_df['deforestation_for_industry']
            biomass_industry = residues_industry + wood_industry + deforestation_industry
            residues_energy = mw_residues_energy
            wood_energy = mw_wood_energy
            biomass_energy = residues_energy + wood_energy + deforestation_energy

            biomass_industry_series = InstanciatedSeries(
                years, biomass_industry.tolist(), 'Biomass dedicated to industry', InstanciatedSeries.BAR_DISPLAY)
            biomass_energy_series = InstanciatedSeries(
                years, biomass_energy.tolist(), 'Biomass dedicated to energy', InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(biomass_industry_series)
            new_chart.add_series(biomass_energy_series)

            instanciated_charts.append(new_chart)

            # biomassdry price per kWh
            new_chart = TwoAxesInstanciatedChart('years', 'Price [$/MWh]',
                                                 chart_name='Biomass dry price evolution', stacked_bar=True)
            mw_price = biomass_dry_df['managed_wood_price_per_MWh']
            deforestation_price = biomass_dry_df['deforestation_price_per_MWh']
            average_price = biomass_dry_df['price_per_MWh']

            mw_price_series = InstanciatedSeries(
                years, mw_price.tolist(), 'Managed wood', InstanciatedSeries.LINES_DISPLAY)
            average_price_series = InstanciatedSeries(
                years, average_price.tolist(), 'Biomass dry', InstanciatedSeries.LINES_DISPLAY)
            deforestation_price_series = InstanciatedSeries(
                years, deforestation_price.tolist(), 'Deforestation', InstanciatedSeries.LINES_DISPLAY)

            new_chart.add_series(mw_price_series)
            new_chart.add_series(deforestation_price_series)
            new_chart.add_series(average_price_series)
            instanciated_charts.append(new_chart)

            # biomass dry price per ton
            new_chart = TwoAxesInstanciatedChart('years', 'Price [$/ton]',
                                                 chart_name='Biomass dry price evolution', stacked_bar=True)
            mw_price = biomass_dry_df['managed_wood_price_per_ton']
            deforestation_price = biomass_dry_df['deforestation_price_per_ton']
            average_price = biomass_dry_df['price_per_ton']

            mw_price_series = InstanciatedSeries(
                years, mw_price.tolist(), 'Managed wood', InstanciatedSeries.LINES_DISPLAY)
            average_price_series = InstanciatedSeries(
                years, average_price.tolist(), 'Biomass dry', InstanciatedSeries.LINES_DISPLAY)
            deforestation_price_series = InstanciatedSeries(
                years, deforestation_price.tolist(), 'Deforestation', InstanciatedSeries.LINES_DISPLAY)

            new_chart.add_series(mw_price_series)
            new_chart.add_series(deforestation_price_series)
            new_chart.add_series(average_price_series)
            instanciated_charts.append(new_chart)

            # capital graph
            techno_capital_df = self.get_sosdisc_outputs('techno_capital')
            lost_capital_df = self.get_sosdisc_outputs('non_use_capital')
            new_chart = TwoAxesInstanciatedChart('years', 'Capital [G$]',
                                                 chart_name='Non use capital due to deforestation<br>and reforestation vs total capital', stacked_bar=True)
            total_capital = techno_capital_df['Forest']  # + \
            # techno_capital_df['Managed_wood']
            lost_capital_forest = lost_capital_df['Forest']
            #lost_capital_mw = lost_capital_df['Managed_wood']

            total_capital_series = InstanciatedSeries(
                years, total_capital.tolist(), 'Total capital', InstanciatedSeries.LINES_DISPLAY)
            lost_capital_forest_series = InstanciatedSeries(
                years, lost_capital_forest.tolist(), 'Non use capital Forest', InstanciatedSeries.BAR_DISPLAY)
#             lost_capital_mw_series = InstanciatedSeries(
# years, lost_capital_mw.tolist(), 'Non use capital Managed wood',
# InstanciatedSeries.BAR_DISPLAY)

            new_chart.add_series(total_capital_series)
            new_chart.add_series(lost_capital_forest_series)
            # new_chart.add_series(lost_capital_mw_series)
            instanciated_charts.append(new_chart)

        return instanciated_charts
