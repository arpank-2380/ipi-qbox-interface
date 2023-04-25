ipi-interface: i-PI interface for Qbox
--------------------------------------
Please cite: A. Kundu, M. Govoni, H. Yang, M. Ceriotti, F. Gygi, and G. Galli, Phys. Rev. Materials 5, L070801
(1) If Kohn-Sham Eigenvalues are calculated, this will be send to i-PI as a string
    Extra string sending is made very flexible. Currently eigenset and iteration timing is implemented.
    But others can be implemented very easily.
    In qbox.py there is a line:
    self.extra_tree_list = ['./iteration/eigenset','./iteration/timing']
    Here in this list just add the other lists.
    Also Extra can now be sent in either (i) xml or (ii) json format.
    For the latter, installed python version must have "xml2dict" package.
    UPDATE: May-2021
            MLWF centers (by compute_mlwf command or set polarization MLWF)respective dipole, quadrupole
            and partial charges on atoms can also be send as a extra string ti i-PI. 

(2) A series of qbox plot commands can be utilized to store wave functions, densities.
    It must be supplied as a list.
    plot_cmd = ["plot -wf n1 file_prefix_1", "plot -wf n2 file_prefix_2"]
    file_prefix should determine the prefix of the filename and should not contain .cube extension.
    Interface would create a directory named cube_files where all cube_files would be stored.
    UPDATE: May-2021
            An option called "plt_cmd_period" which accepts an integer is implemented; so that plot commands
            can be applied not to all MD steps but periodically. Default value is kept 1, i.e storing all cube
            files as originally it was implemented to do iPI-ENMFD el-phonon calculations
             where cube files must be stored for each configurations.

(3) Similar to plot commands, interface now supports a python list of iterative commands (iter_cmd) which can be applied
    periodically by setting the value of  iter_cmd_period. Like "plot_cmd" key, "iter_cmd" key also accepts a python list
    of qbox commands but unlike plot_cmd these commands must be verbatim as described in Qbox manual. 
    This can be used to calculate MLWF centers or charges on atoms periodically.
