"""Clients that get interactions from specific programs.

Here we implement classes that provide interactions obtained from specific
programs and serve them back to i-PI.

"""

# Written by Arpan Kundu to introduce file system based 
# client-server operations for the driver.
#


import sys
import os
import socket
import time

import numpy as np
import ipi.interfaces
from ipi.interfaces.sockets import DriverSocket, Message

class Client(DriverSocket):

    """Base class for the implementation of a client in Python.

    Handles sending and receiving data from the client code.

    Attributes:
        havedata: Boolean giving whether the client calculated the forces.
    """
    #i_step = 0

    def __init__(self, address="localhost", port=31415, mode="unix", _socket=True, infil="input", outfil="output"):
        """Initialise Client.

        Args:
            - address: A string giving the name of the host network.
            - port: An integer giving the port the socket will be using.
            - mode: A string giving the type of socket used - 'inet' or 'unix'.
            - _socket: If a socket should be opened. Can be False for testing purposes.
        """

        if _socket:
            # open client socket
            if mode == "inet":
                _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                _socket.connect((address, int(port)))
                print ("**********Hey it's Client class speaking***************")
            elif mode == "unix":
                try:
                    _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    _socket.connect("/tmp/ipi_" + address)
                except socket.error:
                    print ('Could not connect to UNIX socket: %s' % ("/tmp/ipi_" + address))
                    sys.exit(1)
            else:
                raise NameError("Interface mode " + mode + " is not implemented (should be unix/inet)")
            super(Client, self).__init__(sock=_socket)
        else:
            super(Client, self).__init__(sock=None)

        # allocate data
        self.havedata = False
        self._vir = np.zeros((3, 3), np.float64)
        self._cellh = np.zeros((3, 3), np.float64)
        self._cellih = np.zeros((3, 3), np.float64)
        self._lenextra = np.int32()
        self._nat = np.int32()
        self._callback = None

    def _getforce(self,verbose):                      
        """Dummy _getforce routine. It will read output file and get the necessary data

        This function must be implemented by subclassing or providing a callback function.
        This function is assumed to calculate the following:
            - self._force: The force of the current positions at self._positions.
            - self._potential: The potential of the current positions at self._positions.
        """
        pass

    def _makeinput(self,exit):
        """ Dummy _makeinput routine. It will write the driver input file for next iteration

        This function must be implemented by subclassing or providing a callback function.
        This function is assumed to prepare the input file for the driver
        """
        pass


    def run(self, verbose=True, t_max=None, fn_exit='EXIT'):
        """Serve forces until asked to finish or socket disconnects.

        Serve forces and potential that are calculated in the user provided
        routine _getforce.

        Arguments:
            - verbose: enable priting of step timing information
            - t_max: optional maximum wall clock run time in seconds
            - fn_exit: name of an exit file - will terminate if found
        """

        t0 = time.time()

        fmt_header = '{0:>6s} {1:>10s} {2:>10s}'
        fmt_step = '{0:6d} {1:10.3f} {2:10.3f}'

        if t_max is None:
            print ('Starting communication loop with no maximum run time.')
        else:
            print ('Starting communication loop with a maximum run time of %d seconds.' %(t_max))
            fmt_header += ' {3:>10s}'
            fmt_step += ' {3:10.1f}'

        if verbose:
            header = fmt_header.format('step', 'time', 'avg time', 'remaining')
            print("")
            print(header)
            print(len(header) * '-')

        i_step = 0
        t_step_tot = 0.0
        t_remain = None

        try:
            while True:

                # receive message
                msg = self.recv_msg()

                # process message and respond
                if msg == "":
                    print ("Server shut down.")
                    break
                elif msg == Message("status"):
                    if self.havedata:
                        self.send_msg("havedata")
                    else:
                        self.send_msg("ready")
                elif msg == Message("posdata"):
                    self._cellh = self.recvall(self._cellh)
                    self._cellih = self.recvall(self._cellih)
                    self._nat = self.recvall(self._nat)
                    self._positions = self.recvall(self._positions)
                    t0_step = time.time()
                    self._makeinput(exit=False)
                    self._getforce()
                    if verbose:
                        t_now = time.time()
                        t_step = t_now - t0_step
                        t_step_tot += t_step
                        t_step_avg = t_step_tot / (i_step + 1)
                        if t_max is not None:
                            t_remain = t_max - (t_now - t0)
                        print (fmt_step.format(i_step, t_step, t_step_avg, t_remain))
                    self.havedata = True
                    i_step += 1
                elif msg == Message("getforce"):
                    self.sendall(Message("forceready"))
                    self.sendall(self._potential, 8)
                    self.sendall(self._nat, 4)
                    self.sendall(self._force, 8 * self._force.size)
                    self.sendall(self._vir, 9 * 8)
                    #self.sendall(np.int32(0), 4)
                    self.sendall(np.int32(self._lenextra), 4)
                    if self._lenextra != 0:
                       self.sendall(self._extra, self._sizextra)
                    self.havedata = False
                else:
                    print("Client could not understand command: %s" %msg.decode())
                    self._makeinput(exit=True)
                    break

                # check exit conditions - run time or exit file
                if t_max is not None and time.time() - t0 > t_max:
                    print('Maximum run time of %d seconds exceeded.' %(t_max))
                    self._makeinput(exit=True)
                    break
                if fn_exit is not None and os.path.exists(fn_exit):
                    print('Exit file %s found. Removing file.' %(fn_exit))
                    os.remove(fn_exit)
                    break

        except socket.error as e:
            #print 'Error communicating through socket: [{0}] {1}'.format(e.errno, e.strerror)
            print('Error communicating through socket:'+ str(e.errno) + ' ' + e.strerror)
        except KeyboardInterrupt:
            print(' Keyboard interrupt.')

        print('Communication loop finished.')
        print


