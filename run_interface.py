#!/usr/bin/env python3
import sys 
#place the path where interface is stored. Path must be a string, i.e, within '' or "" 
interface_path = '/home/arpank/ipi+Qbox-interface/interface-py3/src' 
sys.path.insert(0,interface_path)
from interface import interface

interface( run_cmd = 'run 0 60 10',     #It is a string of commands, run commands and others separated by \n; see below
           plot_cmd = None,             #It accepts a python list of plot commands; see below
           plot_cmd_period = 1,         #Periodicity with which plot_cmd would be applied; see below 
           iter_cmd = None,             #It accepts a python list of iterative commands; see below
           iter_cmd_period = 10,        #Periodicity with which iterative commands would be applied; see below 
           store = False,               #if True: it stores all qbox input and outputs
           extra_format = 'xml' )      #Allowed extra formats 'json' or 'xml'


################################################################################################################################
"""                                  More Informations regarding interface                                                  
      Please cite:  A. Kundu, M. Govoni, H. Yang, M. Ceriotti, F. Gygi, and G. Galli, Phys. Rev. Materials 5, L070801       """
#################################################################################################################################
"""                                                   Usage                                                                 """
# Besides the above keywords this executable requires three command line inputs: 
# (1) ipi input file name, 
# (2) qbox input file name that interface will prepare, and 
# (3) qbox output file name where qbox will write outputs and interface would read from it.
# Therefore an example usage of this executable is:
#            python3 path/run_qbox.py ipi_input.xml qbox-input.i qbox-output.r          
                    

"""                                                 run_cmd                                                                  """
# If you want to use more command, for example, to run compute_mlwf it can be done in the following way
# run_cmd = ' run 0 60 10\n compute_mlwf'
# Probably it is better though to apply compute_mlwf using iterative command which by sequence would be applied after plot_cmd



"""                                           plot_cmd (optional)                                                            """
#Remarks:
#---------------------------
#       Optional with default set to None, you can just comment out that line too.
#       This is introduced for calculating electron phonon renormalization where 
#       overlaps between degenerate wavefunctions must be calculated later. 
#       Otherwise, it is recommended not to use this option or use it carefully using 
#       the plot_cmd_period = 100 or 200 etc 
#       This way a few sample wavefunction can be saved on the fly during the PIMD/QTMD
#       By sequence, plot_cmd would be applied after run_cmd but before iter_cmd. 


# Illustration and examples:
#---------------------------
# Each element of a plot_cmd list mustbe exactly as described in qbox documentation with one exception with the file name.
# You would only provide the prefix of the file name. Full file name would be" your prefix + frame + frame_number + .cube.
# An element of this plot_cmd list would looks like
#       plot -density density
# This will create a series of cube files containing densities at each frame. The cube file namaes would be 
# density_frame-1.cube, density_frame-2.cube,......, density_frame-1000.cube...
# Interface would create a directory name cube_files where all these cube_files would be stored.
# More Examples:
#     (1) plot_cmd = ["plot -wf %d wf%d"%(i,i) for i in range(4,8)] will create a list of plot commands
#  or (2) plot_cmd = ["plot -wf 4 wf4","plot -wf 6 wf6", "plot -wf 9 wf9"] 

"""                                          plot_cmd_period (optional)                                                       """
#Remarks
#-------------------------
#    This accepts an integer, to apply plot commands (plt_cmd) periodically. Optional switch with default value set to 1
#    For example, if the chosen value is 10, then those plot commands would be applied every 10th step including the 1st step.


"""                                              iter_cmd (optional)                                                          """
#Remarks:
#--------------------------
#       Optional with default set to None
#       This is introduced for on the fly calculation of MLWF centers, partial charges (response command should not be used).
#       Often such calculations aren't necessary for every MD step, therefore, it is recommended to use this with iter_cmd_period.
#       Please also remember to allow "extra" in output section of the i-PI input.
#       By sequence it would be applied after plot_cmd

# Illustration and examples:
#---------------------------
# Like plot_cmd above, each element of iter_cmd list can be qbox command used verbatim.
# Example: "compute_mlwf" or "partial_charge atom_name radius"
# Caution : response command is not comparible with interface.
# Example-1: 
# iter_cmd = ['compute_mlwf','partial_charge C2 0.5']
# Example-2: 
# Before instatiating the class we can create a list like below,
#      iter_cmd_list1 = ['compute_mlwf']
#      iter_cmd_list2 = ["partial_charge C%d 0.5"%(i) for i in range(1,216)]
#      iter_cmd_list = iter_cmd_list1 + iter_cmd_list2
# Then while instantiating the class, we can supply the list variable iter_cmd_list within the iter_cmd switch as below,
#      interface(run_cmd=...,....., iter_cmd = iter_cmd_list, iter_cmd_periodicity = 10,...)

"""                                            iter_cmd_period(optional)                                                       """
#Remarks
#-------------------------
#    This accepts an integer, to apply iterative commands (iter_cmd) periodically. Optional switch with default value set to 1
#    For example, if the chosen value is 10, then those iterative commands would be applied 
#    every 10th step including the 1st step.
#################################################################################################################################
