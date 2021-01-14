# PyLESA

PyLESA stands for Python for Local Energy Systems Analysis and is pronounced "pai-lee-suh".

PyLESA is an open source tool capable of modelling local energy systems containing both electrical and thermal technologies. It was developed with the aim of aiding the design of local energy systems. The focus of the tool is on modelling systems with heat pumps and thermal storage alongside time-of-use electricity tariffs and predictive control strategies. It is anticipated that the tool provides a framework for future development including electrical battery studies and participation in grid balancing mechanisms.

This tool was developed as part of a PhD, "Modelling and Design of Local Energy Systems Incorporating Heat Pumps, Thermal Storage, Future  Tariffs, and Model Predictive Control " by Andrew Lyden.

PyLESA is compatible with Python 3.7.6.

# Running PyLESA

1.	Install Python 3.7.6. and dependencies in requirements.txt, it is recommended to use an Anaconda Installtion (https://www.anaconda.com/products/individual). Download source code and ensure repository structure includes Inputs and Outputs folders to save processing and outputs.
2.  Define and gather data on the local energy system to be modelled including resources, demands, supply, storage, grid connection, and control strategy. Input these using one of the template Excel Workbooks from the Inputs folder.
3.	Optionally run the demand and resource assessment methods to generate hourly or sub-hourly profiles depending on available data. Input generated profiles, along with the increments and ranges to be modelled within the required parametric design, into the Excel Workbook.
4.	Using a terminal (e.g. PowerShell) navigate to the relevant directory, i.e. “…/PyLESA/PyLESA”, enter “python run.py” and when prompted enter the input Excel workbook filename (excluding the file extension “.xlsx”).
5.	Open the Outputs folder to view the outputs saved to inform the specified analysis.
