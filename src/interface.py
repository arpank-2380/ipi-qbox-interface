import sys
import xml.etree.ElementTree as ET
from qbox import Client_qbox

ipi_input = sys.argv[1]
qbox_input = sys.argv[2]
qbox_output = sys.argv[3]


class interface:
      def __init__(self,run_cmd='run 0 60', plot_cmd=None, plot_cmd_period = 1,\
                        iter_cmd = None, iter_cmd_period = 1, store = False, extra_format = 'xml'): 

          global ipi_input, qbox_input, qbox_output
          #print(ipi_input, qbox_input, qbox_output)
          ipi_input_tree = ET.parse(ipi_input)
          ipi_input_soc_tree = ipi_input_tree.getroot().find("./ffsocket")
          
          try:
              soc_mode = ipi_input_soc_tree.attrib["mode"]
          except KeyError:
              soc_mode = 'inet'
          
          soc_address_tree = ipi_input_soc_tree.find('address')
          if soc_address_tree is not None:
             soc_address = soc_address_tree.text.strip()
          else:
             soc_address = 'localhost'
          
          soc_port_tree = ipi_input_soc_tree.find('port')
          if soc_port_tree is not None:
             soc_port = int(soc_port_tree.text)
          else:
             soc_port = 31415

          if plot_cmd is None:
             plot_cmd = []
          if iter_cmd is None:
             iter_cmd = []
          
          send_extras = False    
          ipi_input_traj_tree = ipi_input_tree.getroot().findall("./output/trajectory")
          for item in ipi_input_traj_tree:
              if item.text.strip() == 'extras':
                 send_extras = True
 
          driver = Client_qbox(address=soc_address, port=soc_port, mode=soc_mode,  infil=qbox_input, \
                       outfil=qbox_output,run_cmd = run_cmd, plot_cmd = plot_cmd, plot_cmd_period = plot_cmd_period,\
                       iter_cmd = iter_cmd, iter_cmd_period = iter_cmd_period, store = store, extra_format = extra_format)

          if not send_extras:
             driver.extra_tree_list=[]
          driver.run(verbose=True)
