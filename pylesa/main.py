import logging
from pathlib import Path
import shutil
import time
from tqdm import tqdm

from . import parametric_analysis
from .controllers import fixed_order
from .controllers import mpc
from .io import inputs, outputs, read_excel
from .io.paths import valid_dir, valid_fpath
from .mp.process import OutputProcess

LOG = logging.getLogger(__name__)

def run_solver(controller: str, subname:  str, outdir: Path, first_hour: int, timesteps: int):
    if controller == 'Fixed order control':
        # run fixed order controller
        LOG.info(f'Running fixed order controller: {subname}')
        fixed_order.FixedOrder(
            outdir, subname).run_timesteps(
                first_hour, timesteps)

    elif controller == 'Model predictive control':
        # run mpc controller
        LOG.info('Running model predictive controller...')
        myScheduler = mpc.Scheduler(
            outdir, subname)
        pre_calc = myScheduler.pre_calculation(
            first_hour, timesteps)
        myScheduler.moving_horizon(
            pre_calc, first_hour, timesteps)

    else:
        msg = f'Unsuitable controller chosen: {controller}'
        LOG.error(msg)
        raise ValueError(msg)

def main(xlsxpath: str, outdir: str, overwrite: bool = False, singlecore: bool = False):
    """Run PyLESA, an open source tool capable of modelling local energy systems.
    
    By default, this function runs the PyLESA solver in the main process but
    outsources the writing of matplotlib files to a second process. The writing
    of matplotlib files takes roughly the same amount of time as the Fixed Order
    solver takes, so there is a significant performance benefit to running
    multiple cores. Multithreading is not an option since the artist functions
    in matplotlib are not necessarily thread safe.

    Args:
        xlsxpath: path to Excel input file\n
        outdir: path to output directory, a sub-directory matching the Excel filename will be created\n
        overwrite: bool flag to overwrite existing output, default: False
        singlecore: bool flag to run on a single core rather than two cores, default: False (uses two cores)
    """
    xlsxpath = valid_fpath(xlsxpath)
    outdir = valid_dir(outdir) / xlsxpath.stem
    if outdir.exists():
        if overwrite:
            try:
                shutil.rmtree(outdir)
            except Exception as e:
                msg = f"Error occurred while attempting to delete {outdir}"
                LOG.error(msg, exc_info=e)
                raise e
        else:
            msg = f"Output directory {outdir} already exists, set --overwrite to force overwriting"
            LOG.error(msg)
            raise FileExistsError(msg)
    outdir.mkdir()

    t0 = time.time()

    # generate pickle inputs from excel sheet
    read_excel.read_inputs(xlsxpath, outdir)

    # generate pickle inputs for parametric analysis
    LOG.info('Generating inputs for all simuation combinations...')
    myPara = parametric_analysis.Para(outdir)
    myPara.create_pickles()
    combinations = myPara.folder_name
    num_combos = len(combinations)

    t1 = time.time()
    tot_time = (t1 - t0)

    LOG.info(f'Input complete. Time taken: {round(tot_time, 2)} seconds.')

    # just take first subname as controller is same in all
    subname = myPara.folder_name[0]
    myInputs = inputs.Inputs(outdir, subname)

    # controller inputs
    controller_info = myInputs.controller()['controller_info']
    controller = controller_info['controller']
    timesteps = controller_info['total_timesteps']
    first_hour = controller_info['first_hour']

    if singlecore:
        # Single core
        for i in tqdm(range(num_combos), desc="Jobs"):
            # combo to be run
            subname = combinations[i]
            run_solver(controller, subname, outdir, first_hour, timesteps)
            # Run output
            outputs.run_plots(outdir, subname)
    else:
        # Run two processes:
        # - main process runs the solver
        # - second process runs the output (to produce matplotlib figures)
        p = OutputProcess()

        try:
            # Start output process
            # Process waits to write output until a job is submitted
            p.start(outputs.run_plots)

            # Run controller for all combinations
            for i in tqdm(range(num_combos), desc="Jobs"):
                # combo to be run
                subname = combinations[i]
                run_solver(controller, subname, outdir, first_hour, timesteps)
                # Submit job to output queue for writing
                p.submit([outdir, subname])

        except Exception as e:
            p.cancel()
            raise e

        finally:
            # Stop output process once job is complete
            p.stop()

    tx = time.time()
    outputs.run_KPIs(outdir)
    ty = time.time()
    tot_time = (ty - tx)
    LOG.info(f'Time taken for running KPIs: {round(tot_time, 2)} seconds')

    t2 = time.time()
    tot_time = (t2 - t1) / 60
    LOG.info(f'Simulations and outputs complete. Time taken: {round(tot_time, 2)} minutes')

    tot_time = (t2 - t0) / 60
    LOG.info(f'Run complete. Time taken: {round(tot_time, 2)} minutes')
