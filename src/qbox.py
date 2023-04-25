"""
This program defines the Client_qbox class which is a daughter of Client class.
This program is responsible for making the input files for the Qbox-driver 
&
reading the Qbox-output files and storing the necessary data in the arrays

"""

### This program is written by Arpan Kundu 


import xml.etree.ElementTree as ET
import numpy as np
import os,sys
import time
from clients import Client

try:
   import xmltodict, json
   json_conv_possible = True
except ImportError:
   json_conv_possible = False
   print(" Package xmltodict is not found.\n Cannot send extra strings in json format. \n It would send extra strings in xml format.\n")



class Client_qbox(Client):

      """
      Stores provided data, initialize the base class and introduces new objects
      """ 
      def __init__(self,address='localhost', port=31415, mode='unix', _socket=True, \
                  infil="input", outfil="output",run_cmd='run 0 100',\
                  iter_cmd = [], iter_cmd_period = 1, plot_cmd = [], plot_cmd_period = 1,\
                  store=False,extra_format='xml'):

          self._potential = np.zeros(1)
          self._symbol = []
          self._species = []
          self._extra = ""
          self.infil = infil 
          self.outfil= outfil
          self.lockfil = self.infil+".lock"
          self.run_cmd=run_cmd
          self.plot_cmd = plot_cmd
          self.plot_cmd_period = plot_cmd_period
          self.iter_cmd = iter_cmd
          self.iter_cmd_period = iter_cmd_period
          self._omega = np.zeros(1)              # simulation cell volume

          ### After running qbox in server mode it immediately creates a .lock file 
          ### We have to remove this lock file to initiate first qbox-calculation
          while not os.path.exists(self.lockfil):
                    time.sleep(1)
          os.remove(self.lockfil)

          ### After 1st qbox calculation it will create outfil and infile.lock. 
          ### Appearance of .lock file will indicate interface that output file is ready to be read.
          while not os.path.exists(self.lockfil):
                    time.sleep(1)

          ### Sending the 1st qbox output to python XML parser
          tree   = ET.parse(self.outfil)
          root   = tree.getroot()         

          ### Read data will initialize the symbol and species list which will be same throughout the whole i-PI simulation
          #print("Initializing the interface from 1st driver calculation")
          for atom in tree.findall('./iteration/atomset/atom'):
              self._symbol.append(atom.attrib['name'])
              self._species.append(atom.attrib['species'])

          #### Checking whether qbox is calculating the stress tensor. If so activate the boolean switch
          if tree.find('./iteration/stress_tensor/') is None:
             self._stress = False                            # whether it will read and process stress related data
          else:
             self._stress = True


          ### Size of the symbol list is used to obtain the number of atoms in the simulation
          self._nat = len(self._symbol)

          ### After obtaining the number of atoms, Numpy array to keep positions and force are initialized
          self._positions = np.zeros((self._nat,3),np.float64)
          self._force = np.zeros((self._nat,3),np.float64)

          self._iter = 0          # keeps tracks iteration count useful for debugging
          self.store = store      # Do you want to store all input and outputs throughout the simulation?

          if self.store:
             os.system("mkdir input_store")
             os.system("mkdir output_store")

          if len(self.plot_cmd) > 0:
             if not os.path.isdir("cube_files"):
                os.system("mkdir cube_files")
          
          self.extra_format=extra_format
        
          #Add tree lists here if you want to send that part of qbox output as extras
          self.extra_tree_list = ['./iteration/eigenset','./iteration/mlwfs','./iteration/mlwf_set',\
                                   './iteration/dipole','./iteration/quadrupole','./iteration/timing', \
                                   './mlwfs', './partial_charge']
          ### Calculating the length and byte-size of the string
          self._lenextra= len(self._extra)
          self._sizextra= sys.getsizeof(self._extra) 
          #print("len = %d size = %d" %(self._lenextra,self._sizextra))   

          # call base class constructor
          super(Client_qbox, self).__init__(address, port, mode, _socket,infil,outfil)

      def extra_string(self,tree,extra_tree='./iteration/eigenset',fmt='xml'):
          fmt=self.extra_format
          if not json_conv_possible:
             fmt='xml'
          extra_string=""
          final_tree_address=None
          # If the property is printed for each scf iteration only the last one would be considered to ensure
          # properties are only send as an extra string when SCF loop is converged.
          if "iteration" in extra_tree:
             for scf_iter in tree.findall(extra_tree):
                 final_tree_address = scf_iter
             if final_tree_address is not None:
                extra_string=ET.tostring(final_tree_address).decode()
                if fmt == 'json':
                   extra_dict=xmltodict.parse(extra_string)
                   extra_string = json.dumps(extra_dict)
                extra_string=extra_string+'\n'
          else:
             for tree_address in tree.findall(extra_tree): 
                 if tree_address is None:
                    break
                 extra_string_temp = ET.tostring(tree_address).decode()
                 if fmt == 'json':
                    extra_dict = xmltodict.parse(extra_string_temp)
                    extra_string_temp = json.dumps(extra_dict)
                 extra_string = extra_string + extra_string_temp + "\n"
          return extra_string



      def _getforce(self,verbose=False):

          """ arg: init = True if already initialized, 
                          False if not initialized. In that case it has to read 1st output from driver
              This method waits for input.lock file to appear. 
              Once it is there it reads the output stores forces and removes input.lock
          """
          if verbose:
             print("Welcome to _getforce")


          ### Waiting for the appearence of the .lock file. Its appearence indicates qbox output is ready to be read
          try:
              while not os.path.exists(self.lockfil):
                    time.sleep(1)
          except KeyboardInterrupt:
              print ("Keyboard interrupt.")

          if verbose:
             print("input.lock found. Reading output") 

          ### Sending qbox-output to python XML parser
          tree   = ET.parse(self.outfil)
          root   = tree.getroot()      

          if verbose:
                print("Reading output from driver \n" )             

          ### Reading and storing potential energy from qbox output
          self._potential[:] = float(tree.find('./iteration/etotal').text)

          ### Reading and storings positions, and forces from qbox output
          _counter = 0
          for atom in tree.findall('./iteration/atomset/atom'):
              self._positions[_counter,:] = [float(x) for x in atom.find('position').text.split()]
              #self._velocity[_counter,:] = [float(x) for x in atom.find('velocity').text.split()]
              self._force[_counter,:] = [float(x) for x in atom.find('force').text.split()]
              _counter+= 1

          ##########################################################################################################
          # Reading and storing  Stress tensors
          # Although stress-tensor is a symmetric matrix
          # This will only return upper triangular matrix to i-PI because
          # i-PI assumes upper triangular matrix for cell parameters and lower-triangular part of stress-tensor will
          # have no effect on variable cell dynamics of i-PI
          ##########################################################################################################

          if self._stress:

             self._omega = float(tree.find('./iteration/unit_cell_volume').text)     # unit cell volume
             au2gpa = 29421.02648438959  # conversion factor of stress: atomic unit ---> GPa (qbox output unit)
              
             self._vir[0,0] = float(tree.find('./iteration/stress_tensor/sigma_xx').text)
             self._vir[1,1] = float(tree.find('./iteration/stress_tensor/sigma_yy').text)
             self._vir[2,2] = float(tree.find('./iteration/stress_tensor/sigma_zz').text)
             self._vir[0,1] = float(tree.find('./iteration/stress_tensor/sigma_xy').text)
             #self._vir[1,0] = self._vir[0,1] 
             self._vir[1,2] = float(tree.find('./iteration/stress_tensor/sigma_yz').text)
             #self._vir[2,1] = self._vir[1,2]
             self._vir[0,2] = float(tree.find('./iteration/stress_tensor/sigma_xz').text)
             #self._vir[2,0] = self._vir[0,2]


          if verbose:
             self._print_read_data()
             
          #### Here "read" stress must be converted into virial || no omega scaling
          if self._stress:
             self._vir = self._omega * self._vir / au2gpa 


          ### Checking whether there are any extra string to be sent e.g. eigenvalues,
          ### maximally localized wannier function calculations etc.

          ### If xmltodict is not available then conversion to JSON is not possible.

          extra=""
          for extra_tree_iter in self.extra_tree_list:
              extra=extra + self.extra_string(tree=tree,extra_tree=extra_tree_iter)



          ### Calculating the length and byte-size of the string
          self._lenextra= len(extra.encode())
          self._sizextra= sys.getsizeof(extra.encode())
         
       
          ### For the moment sending "odd number" of bytes is not possible.
          ### Therefore if "odd number" of bytes are encountered they are converted to even number by
          ### adding a blank space and recalculating the length and bytesize of the string.
          ### Probably this marked block could be removed later, if "odd-even" number of byte problem is solved
          ### ------------------------------------------------------------------------------------------- ### 
          if self._sizextra%2 != 0 and self._lenextra !=0 :
             extra=extra+' '
             self._sizextra= sys.getsizeof(extra.encode())
             self._lenextra=len(extra.encode())
             #self._sizextra=self._sizextra+1
          ### ------------------------------------------------------------------------------------------- ###

          ### When the code will be ported to python3, string encoding mustbe taken care of
          self._extra= extra.encode() 

          #print("len = %d size = %d" %(self._lenextra,self._sizextra))
          #print(self._extra)

          ### If store = True, it will send inputs to input_store directory and outputs to output_store directory
          if self.store:
             outfil_store='output_store/output'+str(self._iter)+'.r'
             os.rename(self.outfil,outfil_store) 
             input_store = 'input_store/input'+str(self._iter)+'.i'
             os.rename(self.infil,input_store)
         
          if len(self.plot_cmd) > 0:
             if self.plot_cmd_period == 1:
                os.system("mv *.cube cube_files")
             elif self._iter % self.plot_cmd_period == 1:  ##by now value of self._iter has increased by 1, so a different if crieteria
                os.system("mv *.cube cube_files") 

      def _makeinput(self,exit,verbose=False):
          """
          This function will write a new input file for qbox-driver
          If exit = True  ===> The new input file will indicate qbox to store the current state in last_sample.xml
                               and quit from the driver mode 

          If exit = False ===> The new input file will move the atoms to the coordinates obtained from i-PI,
                               set the cell parameters to the values obtained from i-PI, and then run SCF calculation
                               based on the given run command that is stored in the string run_cmd
          """

          f= open(self.infil,"w+")        ### Opening/overwriting the Qbox-input file

          if exit:
             print("Saving last qbox sample in last_sample.xml and qutting qbox.")
             f.write("save last_sample.xml\n")
             f.write("quit \n")
          else:
             #f= open(self.infil,"w+")
             if verbose:
                print("preparing input for new coordinates")

             f.write("# input for iteration: %d\n" %(self._iter+1))
             
             # move atoms to a new position
             for i in range(self._nat):
                 f.write(" move %6s to %12.6f %12.6f %12.6f\n" \
                  %(self._symbol[i],self._positions[i,0], self._positions[i,1], self._positions[i,2])) 
             

             # set cell parameters for new input# 
             f.write(" set cell ")
             for i in range(3):
                 for j in range(3):
                     f.write("%12.6f " %(self._cellh[j,i]))
             f.write("\n")
             f.write(" %s \n" %(self.run_cmd))

             if len(self.plot_cmd) > 0:
                if self._iter % self.plot_cmd_period == 0:
                   for cmd in self.plot_cmd:
                       f.write(cmd+"_frame-"+str(self._iter+1)+".cube\n")

             ## Iterative command applyting 1st iteration and then evert "iter_cmd_period"-th iteration
             if len(self.iter_cmd) > 0:
                if self._iter % self.iter_cmd_period == 0:
                   for cmd in self.iter_cmd:
                       f.write(" %s \n" %(cmd))
      
          f.close()

          # Remove .lock file
          if verbose:
             print("Removing "+ self.lockfil )
          os.remove(self.lockfil)

          self._iter+= 1


      def _print_read_data(self):
          """
          This function will print the read data from the qbox output

          """

          print('Qbox output data reading finished.\n Printing the read data for iteration = %d' %(self._iter))
          print('No of atoms: '+str(self._nat))
          print('etotal = %f\n' %(self._potential))
          print('Symbol      Species           X                Y                Z    \
            FX               FY               FZ   \n ')
          for i in range(self._nat):
              print("%6s %12s %16.8f %16.8f %16.8f %16.8f %16.8f %16.8f" \
                       %(self._symbol[i], self._species[i], self._positions[i,0], self._positions[i,1], self._positions[i,2],\
                         self._force[i,0], self._force[i,1], self._force[i,2]))

          if self._stress:
             print('\n')
             print('Omega = %16.8f\n' %(self._omega))
             print(" Stress Tensor (GPa) ")
             print("             X                  Y                 Z       ")
             print("X  %16.8f  %16.8f  %16.8f" %(self._vir[0,0], self._vir[0,1], self._vir[0,2]))
             print("Y  %16.8f  %16.8f  %16.8f" %(self._vir[1,0], self._vir[1,1], self._vir[1,2]))
             print("Z  %16.8f  %16.8f  %16.8f" %(self._vir[2,0], self._vir[2,1], self._vir[2,2]))

