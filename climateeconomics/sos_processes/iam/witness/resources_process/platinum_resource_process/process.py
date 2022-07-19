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

from sos_trades_core.sos_processes.base_process_builder import BaseProcessBuilder
from climateeconomics.core.core_resources.models.platinum_resource.platinum_resource_disc import PlatinumResourceDiscipline


class ProcessBuilder(BaseProcessBuilder):

    # ontology information
    _ontology_data = {
        'label': 'WITNESS Platinum Resource Process',
        'description': '',
        'category': '',
        'version': '',
    }

    PLATINUM_NAME = PlatinumResourceDiscipline.resource_name
   

    def get_builders(self):

        ns_scatter = self.ee.study_name

        ns_dict = {'ns_platinum_resource': ns_scatter,
                   'ns_public': ns_scatter,
                   'ns_resource': ns_scatter,
                   }
        
        mods_dict = {'PlatinumResourceModel': 'climateeconomics.core.core_resources.models.platinum_resource.platinum_resource_disc.PlatinumResourceDiscipline'
                     }
        #chain_builders_resource = self.ee.factory.get_builder_from_module()
        builder_list = self.create_builder_list(mods_dict, ns_dict=ns_dict)
        # builder_list.append(chain_builders_resource)
        return builder_list
