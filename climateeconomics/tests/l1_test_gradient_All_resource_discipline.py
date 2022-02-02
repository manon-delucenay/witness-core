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

from os.path import join, dirname
from pandas import read_csv
from pathlib import Path
from sos_trades_core.execution_engine.execution_engine import ExecutionEngine
from sos_trades_core.tests.core.abstract_jacobian_unit_test import AbstractJacobianUnittest
from climateeconomics.core.core_resources.all_resources_model import AllResourceModel
from climateeconomics.core.core_resources.resources_model import ResourceModel
import unittest
import pandas as pd
import numpy as np


class ResourceJacobianDiscTest(AbstractJacobianUnittest):
    # AbstractJacobianUnittest.DUMP_JACOBIAN = True

    def setUp(self):

        self.name = 'Test'
        self.ee = ExecutionEngine(self.name)

    def analytic_grad_entry(self):
        return [
            self._test_All_resource_discipline_analytic_grad
        ]

    def test_All_resource_discipline_analytic_grad(self):

        self.model_name = 'all_resource'
        ns_dict = {'ns_public': f'{self.name}',
                   'coal_resource': f'{self.name}.{self.model_name}',
                   'oil_resource': f'{self.name}.{self.model_name}',
                   'natural_gas_resource': f'{self.name}.{self.model_name}',
                   'uranium_resource': f'{self.name}.{self.model_name}',
                   'ns_resource': f'{self.name}.{self.model_name}',
                   }

        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_resources.sos_wrapping_all_resource.all_resource_model.all_resource_disc.AllResourceDiscipline'
        builder = self.ee.factory.get_builder_from_module(
            self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes(True)

        data_dir = join(dirname(__file__), 'data')
        self.oil_production_df = read_csv(
            join(data_dir, 'oil.predictible_production.csv'))
        self.oil_production_df.set_index('years', inplace=True)
        self.gas_production_df = read_csv(
            join(data_dir, 'gas.predictible_production.csv'))
        self.coal_production_df = read_csv(
            join(data_dir, 'coal.predictible_production.csv'))
        self.uranium_production_df = read_csv(
            join(data_dir, 'uranium.predictible_production.csv'))
        self.oil_stock_df = read_csv(
            join(data_dir, 'oil.stock.csv'))
        self.gas_stock_df = read_csv(
            join(data_dir, 'gas.stock.csv'))
        self.uranium_stock_df = read_csv(
            join(data_dir, 'uranium.stock.csv'))
        self.coal_stock_df = read_csv(
            join(data_dir, 'coal.stock.csv'))
        self.oil_price_df = read_csv(
            join(data_dir, 'oil.price.csv'))
        self.gas_price_df = read_csv(
            join(data_dir, 'gas.price.csv'))
        self.coal_price_df = read_csv(
            join(data_dir, 'coal.price.csv'))
        self.uranium_price_df = read_csv(
            join(data_dir, 'uranium.price.csv'))
        self.oil_use_df = read_csv(
            join(data_dir, 'oil.use.csv'))
        self.gas_use_df = read_csv(
            join(data_dir, 'gas.use.csv'))
        self.coal_use_df = read_csv(
            join(data_dir, 'coal.use.csv'))
        self.uranium_use_df = read_csv(
            join(data_dir, 'uranium.use.csv'))
        self.non_modeled_resource_df = read_csv(
            join(data_dir, 'resource_data_price.csv'))
        self.all_demand = read_csv(
            join(data_dir, 'all_demand_with_high_demand.csv'))

        self.year_start = 2020
        self.year_end = 2100
        years = np.arange(self.year_start, self.year_end + 1, 1)
        year_range = self.year_end - self.year_start + 1

        values_dict = {f'{self.name}.year_start': self.year_start,
                       f'{self.name}.year_end': self.year_end,
                       f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}': self.all_demand,
                       f'{self.name}.{self.model_name}.oil_resource.{ResourceModel.PRODUCTION}': self.oil_production_df,
                       f'{self.name}.{self.model_name}.oil_resource.{ResourceModel.RESOURCE_STOCK}': self.oil_stock_df,
                       f'{self.name}.{self.model_name}.oil_resource.{ResourceModel.RESOURCE_PRICE}': self.oil_price_df,
                       f'{self.name}.{self.model_name}.oil_resource.{ResourceModel.USE_STOCK}': self.oil_use_df,
                       f'{self.name}.{self.model_name}.natural_gas_resource.{ResourceModel.PRODUCTION}': self.gas_production_df,
                       f'{self.name}.{self.model_name}.natural_gas_resource.{ResourceModel.RESOURCE_STOCK}': self.gas_stock_df,
                       f'{self.name}.{self.model_name}.natural_gas_resource.{ResourceModel.RESOURCE_PRICE}': self.gas_price_df,
                       f'{self.name}.{self.model_name}.natural_gas_resource.{ResourceModel.USE_STOCK}': self.gas_use_df,
                       f'{self.name}.{self.model_name}.coal_resource.{ResourceModel.PRODUCTION}': self.coal_production_df,
                       f'{self.name}.{self.model_name}.coal_resource.{ResourceModel.RESOURCE_STOCK}': self.coal_stock_df,
                       f'{self.name}.{self.model_name}.coal_resource.{ResourceModel.RESOURCE_PRICE}': self.coal_price_df,
                       f'{self.name}.{self.model_name}.coal_resource.{ResourceModel.USE_STOCK}': self.coal_use_df,
                       f'{self.name}.{self.model_name}.uranium_resource.{ResourceModel.PRODUCTION}': self.uranium_production_df,
                       f'{self.name}.{self.model_name}.uranium_resource.{ResourceModel.RESOURCE_STOCK}': self.uranium_stock_df,
                       f'{self.name}.{self.model_name}.uranium_resource.{ResourceModel.RESOURCE_PRICE}': self.uranium_price_df,
                       f'{self.name}.{self.model_name}.uranium_resource.{ResourceModel.USE_STOCK}': self.uranium_use_df,
                       f'{self.name}.{self.model_name}.{AllResourceModel.NON_MODELED_RESOURCE_PRICE}': self.non_modeled_resource_df
                       }
        self.ee.load_study_from_input_dict(values_dict)

        self.ee.execute()

        disc_techno = self.ee.root_process.sos_disciplines[0]
        input_names = []
        input_stock = [
            f'{self.name}.{self.model_name}.{resource}.{ResourceModel.RESOURCE_STOCK}' for resource in AllResourceModel.RESOURCE_LIST]
        input_names.extend(input_stock)
        input_use_stock = [
            f'{self.name}.{self.model_name}.{resource}.{ResourceModel.USE_STOCK}' for resource in AllResourceModel.RESOURCE_LIST]
        input_names.extend(input_use_stock)
        input_price = [
            f'{self.name}.{self.model_name}.{resource}.{ResourceModel.RESOURCE_PRICE}' for resource in AllResourceModel.RESOURCE_LIST]
        input_names.extend(input_price)
        input_other_price = [
            f'{self.name}.{self.model_name}.{AllResourceModel.NON_MODELED_RESOURCE_PRICE}']
        input_names.extend(input_other_price)
        input_demand = [
            f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}']
        input_names.extend(input_demand)
        resource_output = [f'{self.name}.{self.model_name}.{AllResourceModel.ALL_RESOURCE_STOCK}', f'{self.name}.{self.model_name}.{AllResourceModel.All_RESOURCE_USE}',
                           f'{self.name}.{self.model_name}.{AllResourceModel.ALL_RESOURCE_PRICE}', f'{self.name}.{self.model_name}.{AllResourceModel.RATIO_USABLE_DEMAND}']

        #AbstractJacobianUnittest.DUMP_JACOBIAN = True
        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_all_resource_discipline.pkl',
                            discipline=disc_techno, inputs=input_names,
                            outputs=resource_output, step=1e-15,
                            derr_approx='complex_step')