'''
Copyright 2022 Airbus SAS
Modifications on 27/11/2023 Copyright 2023 Capgemini

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
from climateeconomics.glossarycore import GlossaryCore
from sostrades_core.sos_processes.base_process_builder import BaseProcessBuilder


class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'WITNESS economics sectorization process',
        'description': '',
        'category': '',
        'version': '',
    }
    def get_builders(self):

        ns_macro = self.ee.study_name
        ns_scatter = self.ee.study_name 

        ns_dict = {'ns_witness': ns_scatter,
                   'ns_macro': ns_macro,
                   'ns_public': ns_scatter,
                   'ns_functions': ns_scatter,
                   'ns_ref': ns_scatter,
                   'ns_sectors': ns_macro
                   }

        mods_dict = {'Macroeconomics': 'climateeconomics.sos_wrapping.sos_wrapping_sectors.macroeconomics.macroeconomics_discipline.MacroeconomicsDiscipline',
                     f'Macroeconomics.{GlossaryCore.SectorServices}': 'climateeconomics.sos_wrapping.sos_wrapping_sectors.services.services_discipline.ServicesDiscipline' ,
                     f'Macroeconomics.{GlossaryCore.SectorAgriculture}':'climateeconomics.sos_wrapping.sos_wrapping_sectors.agriculture.agriculture_discipline.AgricultureDiscipline',
                     f'Macroeconomics.{GlossaryCore.SectorIndustry}':'climateeconomics.sos_wrapping.sos_wrapping_sectors.industrial.industrial_discipline.IndustrialDiscipline'
                     }
        builder_list = self.create_builder_list(mods_dict, ns_dict=ns_dict)

        return builder_list
