#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import subprocess
import json
import os, glob
import sys

"""
This script will get last version of sitelogs from M3G repository and write them
in an observatory dependent subfolder set in 'observatories'.
The -d --delete option will delete old version as to get only last version even
in a name changing case.
The -o --obsevatory option will download sitelogs for the specified observatory
only. Possible values : OVSM|OVSG|OVPF|REVOSIMA 
USE :


* OUTPUTFOLDER : Folder where to write the downloaded sitelogs.

OPTION :

* -d : delete : Delete old sitelogs in storage folder. This allows to have only
                the last version, as version changing sitelogs changes of name.

* -o : observatory : A four character observatory ID that will be used to filter
                     sitelogs to download. Valid values are : OVSM|OVSG|OVPF|REVOSIMA.

* -r : root folder : per default, an observatory-specific folder is created
                     to store the corresponding sitelogs.
                     This option stores them in OUTPUTFOLDER's root 
                    
* -s : svn : a mode to maintain the legacy OVS's SVN folders.
             download the sitelog of a single obs and perform a 'svn commit'
             a single observatory must be given with -o option.
             the root folder option is automatically activated (-r)


EXAMPLE:

./get_m3g_sitelogs.py OUTPUTFOLDER (-d) (-o OVSM|OVSG|OVPF|REVOSIMA) (-r) (-s)

2021-10-18 FL
"""

def get_m3g_sitelogs(sitelogsfolder, delete, observatory=None,
                     root_folder=False,
                     svn_mode=False):
    
    # the root folder option is automatically activated for the SVN mode
    if svn_mode:
        root_folder = True
    
    # a single observatory must be given for the SVN mode
    if svn_mode and not observatory:
        sys.exit("when using SVN mode (-s), a single observatory must be given with -o option")
        
    # M3G country webservice. We use countries to filter IPGP's obs stations.
    country_url = 'https://gnss-metadata.eu/v1/sitelog/metadata-list?country='

    # Observatories. First field is the counrty code in M3G's webservice.
    # Second field is the name of the observatory and is used to build the subfolder
    observatories = {'MTQ' : 'OVSM',
                     'GLP' : 'OVSG',
                     'BLM' : 'OVSG',       ### St Barthelemy
                     'MAF' : 'OVSG',       ### St Martin (no station there for the moment)
                     'REU' : 'OVPF',
                     'MYT' : 'REVOSIMA',
                     'ATF' : 'REVOSIMA'}   ### TAAF aka Terres Australes 

    # If an observatory ID is given, only download its sitelogs
    
    if observatory in observatories.values():
        observatories_clean = dict()
        for obs_key,obs_val in observatories.items():
            if obs_val in observatory:
                observatories_clean[obs_key] = obs_val
        
        observatories = observatories_clean
        
        ## simple way to filter observatories if observatories is bijective
        ## not the case anymore because ATF, BLM ... (2022-10)
        #obs_key = list(observatories.keys())[list(observatories.values()).index(observatory)]
        #observatories = {obs_key: observatories[obs_key]}

    # Check that output folder exists
    if not os.path.exists(sitelogsfolder):
        print('# ERROR : : The output folder for log file doesn\'t exist')
        return

    # Check that obs' subfolder exists. If not, creates.
    for obs in [*observatories.values()]:
        if not root_folder:
            obs_path = os.path.join(sitelogsfolder, obs)
        else:
            obs_path = sitelogsfolder
            
        if not os.path.exists(obs_path):
            os.mkdir(obs_path)

    Sitelog_local_paths = []
    
    for obs in observatories.keys():

        obs_url = country_url + obs

        obs_infos = requests.get(obs_url)
        obs_infos = obs_infos.content.decode('utf-8')
        obs_infos = obs_infos.splitlines()
        obs_infos = obs_infos[1:] # remove header
        
        if not root_folder:
            obs_path = os.path.join(sitelogsfolder, observatories[obs])
        else:
            obs_path = sitelogsfolder
            
        # If delete, empty folders
        if delete:
            old_sitelogs = glob.glob(obs_path + '/*log')
            for f in old_sitelogs:
                os.remove(f)

        print("### Downloading {} ({}) sitelogs from M3G to {}".format(observatories[obs],obs,obs_path))

        for line in obs_infos:
            line = line.split()

            # station_name = line[0]

            # If station is declared in M3G but sitelog not available yet
            if len(line) < 6:
                print('### ' + line[0] + ' : not available ###')
                continue

            sitelog_url = line[6]
            sitelog_name = line[3]
            sitelog_local_path = os.path.join(obs_path, sitelog_name)
            Sitelog_local_paths.append(sitelog_local_path)

            print('### ' + sitelog_name + ' ###')

            # Dowload the sitelog
            # r = requests.get(sitelog_url, allow_redirects=True)
            # print(r.status_code)
            # open(os.path.join(obs_path, sitelog_name), 'wb').write(r.content)
            subprocess.call(['wget', '--no-check-certificate', sitelog_url, '-q', '-O', sitelog_local_path])
    
    if svn:
        print("### SVN add/commit of the downloaded sitelogs")
        for sitelog_local in Sitelog_local_paths:
            subprocess.call(['svn', 'add', sitelog_local])
        subprocess.call(['svn', 'commit', '-m', 'get_m3g_sitelogs auto commit', sitelogsfolder])

    # # Other tecnhique using node webservice that will send back less information
    # # about the sitelogs but will filter with the node ID, and will return all
    # # sitelogs belonging to IPGP node
    #
    # node_url = "https://gnss-metadata.eu/v1/node/view?id="
    # node_id = '5e4d07d9468524145a7cf0f2' # IPGP
    #
    # sitelog_url = "https://gnss-metadata.eu/v1/sitelog/exportlog?id="
    #
    # # Getting station list related to IPGP node
    # node_url = node_url + node_id
    #
    # node_infos = requests.get(node_url)
    # node_infos = node_infos.content.decode('utf-8')
    # node_infos = json.loads(node_infos)
    #
    # station_list = node_infos['stations']
    #
    # for station in station_list:
    #
    #     output = os.path.join(sitelogsfolder, observatories[station[-3:]], station.lower() + '.log')


if __name__ == '__main__':

    import argparse

    # Parsing Args
    parser = argparse.ArgumentParser(description='Get all IPGP sitelogs in the last version for M3G repository')
    parser.add_argument('sitelogsfolder', type=str, help='Output folder where to store downloaded sitelogs')
    parser.add_argument('-d', '--delete', help='Delete old sitelogs in storage folder', action='store_true')
    parser.add_argument('-o', '--observatory', help='Download sitelog for a single observatory (OVSM|OVSG|OVPF|REVOSIMA)',
                        type=str, choices=['OVSM', 'OVSG', 'OVPF', 'REVOSIMA'], default=None)
    parser.add_argument('-r', '--root', help='store the sitelogs in OUTPUTFOLDER root',action='store_true',default=False)
    parser.add_argument('-s', '--svn', help='a mode to maintain the legacy OVS SVN folder. Download the sitelog of a single obs and perform a svn commit',action='store_true',default=False)

    args = parser.parse_args()
    sitelogsfolder = args.sitelogsfolder
    delete = args.delete
    observatory = args.observatory
    svn = args.svn
    root = args.root

    get_m3g_sitelogs(sitelogsfolder, delete, observatory,root,svn)
