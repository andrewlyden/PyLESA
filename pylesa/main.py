from pathlib import Path
import time

from . import read_excel
from . import parametric_analysis
from . import inputs
from . import fixed_order
from . import mpc
from . import outputs

def main(xlsxpath: str):
    """Entry point for the PyLESA programme
    
    Args:
        xlsxpath: path to Excel input file
    """
    xlsxpath = Path(xlsxpath).resolve()
    if not xlsxpath.exists():
        msg = f"File {xlsxpath} does not exist"
        raise FileNotFoundError(msg)
    
    name = str(xlsxpath)

    t0 = time.time()

    # # generate pickle inputs from excel sheet
    read_excel.run_all(name)

    # generate pickle inputs for parametric analysis
    print('Generating inputs for all simuation combinations...')
    myPara = parametric_analysis.Para(name)
    myPara.create_pickles()
    combinations = myPara.folder_name
    num_combos = len(combinations)

    t1 = time.time()
    tot_time = (t1 - t0)

    print('Input complete. Time taken: ', round(tot_time, 2), 'seconds.')

    # just take first subname as controller is same in all
    subname = myPara.folder_name[0]
    myInputs = inputs.Inputs(name, subname)

    # controller inputs
    controller_info = myInputs.controller()['controller_info']
    controller = controller_info['controller']
    timesteps = controller_info['total_timesteps']
    first_hour = controller_info['first_hour']

    # run controller and outputs for all combinations
    for i in range(num_combos):

        # combo to be run
        subname = combinations[i]

        if controller == 'Fixed order control':
            # run fixed order controller
            print('Running fixed order controller...')
            fixed_order.FixedOrder(
                name, subname).run_timesteps(
                    first_hour, timesteps)

        elif controller == 'Model predictive control':
            # run mpc controller
            print('Running model predictive controller...')
            myScheduler = mpc.Scheduler(
                name, subname)
            pre_calc = myScheduler.pre_calculation(
                first_hour, timesteps)
            myScheduler.moving_horizon(
                pre_calc, first_hour, timesteps)

        else:
            raise Exception('Unsuitable controller chosen...')

        print('Running output analysis...')
        # run output analysis
        outputs.run_plots(name, subname)

    tx = time.time()
    outputs.run_KPIs(name)
    ty = time.time()
    tot_time = (ty - tx)
    print('Time taken for running KPIs: ', round(tot_time, 2), 'seconds')

    t2 = time.time()
    tot_time = (t2 - t1) / 60

    print('Simulations and outputs complete. Time taken: ', round(tot_time, 2), 'minutes')

    tot_time = (t2 - t0) / 60

    print('Run complete. Time taken: ', round(tot_time, 2), 'minutes')
