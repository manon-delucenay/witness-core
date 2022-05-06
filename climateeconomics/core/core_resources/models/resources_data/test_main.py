from copy import deepcopy
from os.path import join, dirname
import random as rd
from tkinter import Y

from matplotlib import use
from energy_models.core.stream_type.resources_models.resource_glossary import ResourceGlossary
import pandas as pd
import numpy as np

coal_name=ResourceGlossary.Coal['name']
copper_name=ResourceGlossary.Copper['name']

year_start = 2020
year_end = 2100
years = np.arange(year_start, year_end + 1)
lifespan = 30
new_stock = 47

copper = pd.read_csv(join(dirname(__file__), f'../resources_data/{copper_name}_consumed_data.csv')) #pd.read_csv(join(dirname(__file__),'copper_resource_consumed_data.csv')) ou : pd.DataFrame(columns= ['years' , 'copper_consumption' ])
copper_production_data = pd.read_csv(join(dirname(__file__), f'../resources_data/{copper_name}_production_data.csv'))

coal = pd.read_csv(join(dirname(__file__), f'../resources_data/{coal_name}_consumed_data.csv'))
coal_production_data = pd.read_csv(join(dirname(__file__), f'../resources_data/{coal_name}_production_data.csv'))

use_stock = pd.DataFrame(
            {'years': np.insert(years, 0, np.arange(year_start - lifespan, year_start, 1))})
print(use_stock)
# copper_dict = copper.to_dict()
# print(copper_dict['copper_consumption'].values)

copper_sub_resource_list = [col for col in list(copper_production_data.columns) if col != 'years']
copper_dict = {}
for resource_type in copper_sub_resource_list:
    use_stock[resource_type] = np.insert(np.zeros(len(years)-1), 0, copper[f'{resource_type}_consumption'])
print(use_stock['copper'])

coal_sub_resource_list = [col for col in list(coal_production_data.columns) if col != 'years']
coal_dict = {}
for resource_type in coal_sub_resource_list:
    
    coal_dict[resource_type] = coal[f'{resource_type}_consumption'].values

print (coal_dict)    


"""copper_oui= copper.to_dict()

year = 2021
year_end = 2101

years = np.arange(year, year_end)

copper_test = pd.DataFrame({'years': years , 'copper_consumption': np.linspace(0, 0, len(years))})

copper_new = pd.concat([copper, copper_test], ignore_index=True)
copper_dict = copper_new.to_dict()

# print("copper dataframe: \n")
# print(copper)
# print("copper dico : \n")
# print(copper_oui)





#test insert function

lifespan = 30
test = np.arange(1, 6, 1)
test = np.zeros(len(test))

fonction_test = np.insert(years, 0, np.arange(year - lifespan , year, 1))

fonction_test = np.insert(fonction_test, 0, test[:-1])

#print(test)

#print(copper_dict['copper_consumption'])


#visualisation

oui = copper['copper_consumption'].values

available_resource = deepcopy(oui[6:])

#print (available_resource)


#######

#regarder de plus près le dataframe usestock
# print(" copper consumed normal : \n")
# print(copper['copper_consumption'])
# print("\n")
# print("on insère au début unn truc férent\n")
# copper['copper_consumption'] = np.insert(copper['copper_consumption'], 0, resource_consumed_data['sub_bituminous_and_lignite_consumption'])
# print(copper['copper_consumption'])

"""