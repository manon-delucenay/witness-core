# ClimateEconomics


## Description
ClimateEconomics is the Python package to evaluate the effect of energy way of production on climate change and macro-economy.

## Prerequisite
In order to satisfy dependencies, following prerequisites need to be satisfied:
* deployment of gemseo package and its requirements (see requirements.txt of gemseo package)
* deployment of energy\_models package and its requirements (see requirements.in of energy\_models package)
* deployment of sostrades\_core\_package and its requirements (see requirements.in of sostrades\_core\_package package)
* libraries in requirements.in

The following command can be used to install the package listed in requirements.in
$$pip install -r requirements.in --trusted-host pypi.org --trusted-host files.pythonhosted.org$$


## Overview

This package contains the following disciplines:
* agriculture, to determine the area taken by food to feed humanity
* resources (coal, gas, oil, uranium), to evaluate to quantity left and the extraction price of resources.
* carboncycle, to take into account the natural cycle of carbon
* carbonemissions, to evaluate the quantity of CO2 emitted
* damagemodel, to evaluate the impact of environmental damage on the economy
* macroeconomics, the evaluate different indicator of the global economy
* policymodel, to evaluate the price of the CO2 taxes
* population, to evaluate the global population
* tempchange, to evaluate the change of temperature
* utility, to evaluate the utility

For more information, please look at the documentation associated.

Models are in **core** folder. Disciplines and associated documentations are in **sos\_wrapping folder**.
To create a documentation associated to a discipline, create a **documentation** folder in **sos\_wrapping/discipline_folder** and name the documentation file as the discipline file, disc\_file\_name.markdown.
Processes(couple several disciplines) and usecases(process with specific inputs) are in sos\_processes folder. 
To run a usecase, run usecase.py file as Python run.

Associated tests are in tests folder.
l0 tests are unitary tests. They are used for stand alone disciplines and models.
l1 tests are used to test gradient computation of disciplines and usecases.
l2 tests are used to test gradient computation of process.
To run a test, run test.py file as Python unit-test.
To run all test, use the command *nose2* .

documentation folder gives details about the optimisation problem formulation.

## Contributing

## Communicating with the SoSTrades team

## Looking at the future

### Regionalization

At the moment, results given by Witness process and the different models are global results which are an average over the world.
In order to have more accuracy, we want to add regionalization aspect. The first step is to propose a regionalisation continent by continent.

## License 
The witness-core source code is distributed under the Apache License Version 2.0.
A copy of it can be found in the LICENSE file.

The witness-core product depends on other software which have various licenses.
The list of dependencies with their licenses is given in the CREDITS.rst file.
