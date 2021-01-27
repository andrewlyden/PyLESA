# PyLESA

PyLESA stands for Python for Local Energy Systems Analysis and is pronounced "pai-lee-suh".

PyLESA is an open source tool capable of modelling local energy systems containing both electrical and thermal technologies. It was developed with the aim of aiding the design of local energy systems. The focus of the tool is on modelling systems with heat pumps and thermal storage alongside time-of-use electricity tariffs and predictive control strategies. It is anticipated that the tool provides a framework for future development including electrical battery studies and participation in grid balancing mechanisms.

This tool was developed as part of a PhD, "Modelling and Design of Local Energy Systems Incorporating Heat Pumps, Thermal Storage, Future  Tariffs, and Model Predictive Control" by Andrew Lyden.

# Running PyLESA

1.	Install Python3 (code has only been tested on Python 3.7.6. but should work with similar) and dependencies in requirements.txt, it is recommended to use an Anaconda Installation (https://www.anaconda.com/products/individual) as these will contain the majority of required packages. Download source code.
2.  Define and gather data on the local energy system to be modelled including resources, demands, supply, storage, grid connection, and control strategy. Define the increments and ranges to be modelled within the required parametric design. Input all this data using one of the template Excel Workbooks from the 'inputs' folder.
3.	Optionally run the demand (heat_demand.py and electricity_demand.py) and resource assessment methods (see PhD thesis for details) to generate hourly profiles depending on available data. Input generated profiles into the Excel Workbook.
4.	Using a terminal (e.g. PowerShell) navigate to the relevant directory, e.g. “…/PyLESA-1.1/PyLESA”, enter “python run.py” and when prompted enter the input Excel workbook filename (excluding the file extension “.xlsx”).
5.	After the run is complete, open the Outputs folder to view the KPI 3D plots and/or operational graphs, as well as .csv outputs. (Note an error will be raised if only one simulation combination is run, as 3D plots cannot be processed.) There are also raw outputs.pkl file for each simulation combination which contains a vast range of raw outputs.

Video on running PyLESA: https://youtu.be/QsJut9ftCT4
