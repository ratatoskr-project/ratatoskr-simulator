#!/bin/python

# Copyright 2018 Jan Moritz Joseph

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
###############################################################################
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import csv
import numpy as np
from joblib import Parallel, delayed
import pickle
import pandas as pd
from combine_hists import combine_VC_hists, combine_Buff_hists,\
init_data_structure
import sys
sys.path.insert(0, '..')
from configure import Configuration
###############################################################################


def main():
    """ Run the script """
    os.system('cp ../config.xml config/config.xml')
    os.system('cp ../network.xml config/network.xml')
    os.system('cp /home/joseph/tmp/ratatoskr-simulator/simulator/sim .')
    config = Configuration('../config.ini')
    results = begin_all_sims(config)
    save_results(results, 'rawResults.pkl')
###############################################################################


def write_config_file(config, configFileSrc, configFileDst, injectionRate):
    """
    Write the configuration file for the urand simulation.

    Parameters:
        - config: configuration object.
        - configFileSrc: the source of the configuration file.
        - configFileDst: the destination of the config file.
        - injectionRate: the injection rate.

    Return:
        - None.
    """
    try:
        configTree = ET.parse(configFileSrc)
    except Exception:
        raise

    configTree.find('noc/nocFile').text = 'config/' + config.topologyFile + '.xml'
    configTree.find('general/simulationTime').set('value', str(config.simulationTime))
    configTree.find('general/outputToFile').set('value', 'true')
    configTree.find('general/outputToFile').text = 'report'

    for elem in list(configTree.find('application/synthetic').iter()):
        if elem.get('name') == 'warmup':
            elem.find('start').set('min', str(config.warmupStart))
            elem.find('start').set('max', str(config.warmupStart))
            elem.find('duration').set('min',
                     str(config.warmupStart + config.warmupDuration))
            elem.find('duration').set('max',
                     str(config.warmupStart + config.warmupDuration))
            elem.find('injectionRate').set('value', str(injectionRate))
        if elem.get('name') == 'run':
            elem.find('start').set('min', str(config.runStart))
            elem.find('start').set('max', str(config.runStart))
            elem.find('duration').set('min', str(config.runStart + config.runDuration))
            elem.find('duration').set('max', str(config.runStart + config.runDuration))
            elem.find('injectionRate').set('value', str(injectionRate))
    configTree.write(configFileDst)
###############################################################################


def write_sim_files(config, simdir):
    """
    Write the files that are associated with each run of the simulation
    (the executable sim + the configuration file).

    Parameters:
        - config: configuration object.
        - simdir: the path of the simulation directory.

    Return:
        - None.
    """
    confdir = simdir + '/config'
    shutil.rmtree(simdir, ignore_errors=True)

    try:
        os.makedirs(simdir)
        os.makedirs(confdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    shutil.copy('sim', simdir)
    shutil.copy(config.libDir + '/' + config.topologyFile + '.xml', confdir)
###############################################################################


def run_indivisual_sim(simdir, basedir):
    """
    Run an individual simulation.

    Parameters:
        - simdir: the path to the simulatin directory.
        - basedir: the path to root of all simulations.

    Return:
        - None.
    """
    os.chdir(simdir)
    args = ('./sim')
    outfile = open('log', 'w')

    try:
        subprocess.run(args, stdout=outfile, check=True)
    except subprocess.CalledProcessError:
        pass

    outfile.flush()
    outfile.close()
    os.chdir(basedir)
###############################################################################


def get_performances(results_file):
    """
    Read the resulting latencies from the csv file.

    Parameters:
        - results_file: the path to the result file.

    Return:
        - A list of the filt, packet and network latencies.
    """
    performance_report = {}
    csv_data = pd.read_csv(results_file)
    for index, row in csv_data.iterrows():
            performance_report[row[0]] = row[1]
    return performance_report
    #latencies = []
    #try:
    #    with open(latencies_results_file, newline='') as f:
    #        spamreader = csv.reader(f, delimiter=' ', quotechar='|')
    #        for row in spamreader:
    #            latencies.append(row[1])
    #except Exception:
    #    # Add dummy values to latencies, -1.
    #    latencies.append(-1)
    #    latencies.append(-1)
    #    latencies.append(-1)

    #return(latencies)
###############################################################################


def begin_individual_sim(config, restart, injectionRates, injIter):
    """
    Begin a simulation with a specif injection rate.

    Parameters:
        - config: configuration object.
        - restart: the index of restarts.
        - injectioRates: the list of injection rates.
        - injIter: the index of the injection rate to be run.

    Return:
        - None.
    """
    print('Simulation with injection rate: ' + str(injectionRates[injIter])
            + ' restart ' + str(restart))
    currentSimDir = config.simDir + str(restart)
    currentConfDir = currentSimDir + '/config'
    write_sim_files(config, currentSimDir)
    write_config_file(config, 'config/config.xml', currentConfDir + '/config.xml',
                      injectionRates[injIter])
    run_indivisual_sim(currentSimDir, config.basedir)
###############################################################################


def begin_all_sims(config):
    """
    Begin all simulations.

    Parameters:
        - config: configuration object.

    Retrun:
        - results: a dictionary of the results.
    """
    print('Generating urand simulation with injection rate from ' +
    str(config.runRateMin) + ' to ' + str(config.runRateMax) + ' steps ' +
    str(config.runRateStep))

    # Initialze the latencies.
    if config.runRateMin == config.runRateMax:
        injectionRates = [config.runRateMin]
    else:
        injectionRates = np.arange(config.runRateMin, config.runRateMax, config.runRateStep)
    injectionRates = [round(elem, 4) for elem in injectionRates]
    latenciesFlit = -np.ones((len(injectionRates), config.restarts))
    latenciesPacket = -np.ones((len(injectionRates), config.restarts))
    latenciesNetwork = -np.ones((len(injectionRates), config.restarts))
    latencies = -np.ones((len(injectionRates), config.restarts))
    bcLatency = -np.ones((len(injectionRates), config.restarts))
    wcLatency = -np.ones((len(injectionRates), config.restarts))
    bcPacketLatency = -np.ones((len(injectionRates), config.restarts))
    wcPacketLatency = -np.ones((len(injectionRates), config.restarts))
    bcNetworkLatency = -np.ones((len(injectionRates), config.restarts))
    wcNetworkLatency = -np.ones((len(injectionRates), config.restarts))
    bcFlitLatency = -np.ones((len(injectionRates), config.restarts))
    wcFlitLatency = -np.ones((len(injectionRates), config.restarts))

    # Run the full simulation (for all injection rates).
    injIter = 0
    VCUsage = []
    BuffUsage = []
    for inj in injectionRates:
        print('Starting Sims with ' + str(config.numCores) + ' processes')
        Parallel(n_jobs=config.numCores)(delayed(begin_individual_sim)
        (config, restart, injectionRates, injIter) for restart in range(config.restarts))

        VCUsage_inj = [pd.DataFrame() for i in range(3)]
        BuffUsage_inj = init_data_structure()  # a dict of dicts
        # Run the simulation several times for each injection rate.
        for restart in range(config.restarts):
            currentSimdir = 'sim' + str(restart)
            lat = get_performances(currentSimdir + '/report_Performance.csv')
            latenciesFlit[injIter, restart] = lat["avgFlitLat"]
            latenciesPacket[injIter, restart] = lat["avgPacketLat"]
            latenciesNetwork[injIter, restart] = lat["avgNetworkLat"]
            latencies[injIter, restart] = lat["avgLat"]
            bcLatency[injIter, restart] = lat["bcLat"]
            wcLatency[injIter, restart] = lat["wcLat"]
            bcPacketLatency[injIter, restart] = lat["bcPacketLat"]
            wcPacketLatency[injIter, restart] = lat["wcPacketLat"]
            bcNetworkLatency[injIter, restart] = lat["bcNewtorkLat"]
            wcNetworkLatency[injIter, restart] = lat["wcNetworkLat"]
            bcFlitLatency[injIter, restart] = lat["bcFlitLat"]
            wcFlitLatency[injIter, restart] = lat["wcFlitLat"]

            VCUsage_run = combine_VC_hists(currentSimdir + '/VCUsage')
            if VCUsage_run is not None:
                for ix, layer_df in enumerate(VCUsage_run):
                    VCUsage_inj[ix] = pd.concat([VCUsage_inj[ix], layer_df])
            BuffUsage_run = combine_Buff_hists(currentSimdir + '/BuffUsage')
            if BuffUsage_run is not None:
                for l in BuffUsage_inj:
                    for d in BuffUsage_inj[l]:
                        BuffUsage_inj[l][d] = BuffUsage_inj[l][d].add(
                                BuffUsage_run[l][d], fill_value=0)
            # input('press any key')
            shutil.rmtree(currentSimdir)

        # Calculate the average and std for VC usage.
        VCUsage_temp = []
        for df in VCUsage_inj:
            if not df.empty:
                VCUsage_temp.append(df.groupby(df.index).agg(['mean', 'std']))
        VCUsage.append(VCUsage_temp)

        # Average the buffer usage over restarts.
        BuffUsage_temp = init_data_structure()  # a dict of dicts
        for l in BuffUsage_inj:
            for d in BuffUsage_inj[l]:
                BuffUsage_temp[l][d] = np.ceil(BuffUsage_inj[l][d] / config.restarts)
        BuffUsage.append(BuffUsage_temp)

        injIter += 1

    print('Executed all sims of all injection rates.')

    results = {'latenciesFlit': latenciesFlit,
               'latenciesNetwork': latenciesNetwork,
               'latenciesPacket': latenciesPacket,
               'latencies' : latencies,
               'injectionRates': injectionRates,
               'VCUsage': VCUsage,
               'BuffUsage': BuffUsage}
    return results
###############################################################################


def save_results(results, results_file):
    """
    Save the results to a pickle file.

    Parameters:
        - results: a dictionary of the results.
        - result_file: the path to the pickle file.

    Return:
        - None.
    """
    with open(results_file, 'wb') as f:
        pickle.dump(results, f)
###############################################################################


if __name__ == '__main__':
    main()
