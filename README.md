# PyLESA

PyLESA stands for Python for Local Energy Systems Analysis and is pronounced "pai-lee-suh".

PyLESA is an open source tool capable of modelling local energy systems containing both electrical and thermal technologies. It was developed with the aim of aiding the design of local energy systems. The focus of the tool is on modelling systems with heat pumps and thermal storage alongside time-of-use electricity tariffs and predictive control strategies. It is anticipated that the tool provides a framework for future development including electrical battery studies and participation in grid balancing mechanisms.

This tool was developed as part of a PhD, "Modelling and Design of Local Energy Systems Incorporating Heat Pumps, Thermal Storage, Future  Tariffs, and Model Predictive Control " by Andrew Lyden.

PyLESA is compatible with Python 3.7.6.

# Running PyLESA

1.	Define and gather data on the local energy system to be modelled including resources, demands, supply, storage, grid connection, and control strategy.
2.	Optionally run the demand and resource assessment methods to generate hourly or sub-hourly profiles depending on available data from step 1.
3.	Input the relevant input data from steps 1 and 2 on the local energy system into the input Excel workbook.
4.	Input the increments and ranges to be modelled within the required parametric design into the input Excel workbook.
5.	Run PyLESA for the specified analysis.
  5.1.	Using a terminal (e.g. PowerShell) navigate to the relevant directory, i.e. “…/PyLESA/PyLESA”.
  5.2.	Enter “python run.py”.
  5.3.	When prompted enter the input Excel workbook filename (excluding the file extension “.xlsx”).
6.	Analyse the outputs saved in the “outputs” folder, particularly the KPIs, to inform the specified analysis.
