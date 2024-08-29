#!/bin/bash
#SBATCH --job-name=ipi-qb
#SBATCH --time=2:00:00             # MAXIMUM WALLTIME
#SBATCH --partition=gagalli-brdwl,gagalli-csl,gagalli-ivyb     # GALLI GROUP PRIVATE PARTITION
#SBATCH --nodes=1                   # NUMBER OF NODES TO USE
#SBATCH --ntasks-per-node=20
##SBATCH --qos=gagalli-debug
##SBATCH --contiguous

#########  Number of  Qbox instances  ################
instance=1

############################ Input/Output Filenames ###############################################
#******** i-PI related *******
ipi_input=input.xml  # i-pi input file (full path or path relative to submission directory)
total_steps=5000     # number of last simulation step; required for dependency jobs 
total_time=6600      # time (seconds) after which i-pi would prepare for a clean exit
ipi_log=ipi.log      # name of the i-pi logfile

#******* Qbox related ********
qbox_opts="-nstb 2"         #Qbox command line options
qbox_initial=qbox-init.i    # To initiate Qbox driver (full path or path relative to submission directory)
qbox_input=input.i          # Regular input file; should be consistent with interface executable
qbox_output=output.r        # Regular output file; should be consistent with interface executable
qbox_log=qbox.log           # qbox-server log file

########################## i-PI+Qbox interface executable path ########################################
# Takes three arguments in the following order ipi_input, qbox_input and qbox_output
interface=../run_interface.py #full path or path-relative to the instance directories (one directory lower to submission directory)

######################### i-PI & Qbox related environment and modules #################################
########################          Change paths if required            ################################
export PYTHONUNBUFFERED=TRUE   ### Python environment variable so that outputs are flushed every step
#module load python
#source /home/arpank/i-pi/env.sh
module load i-pi

#************ Loading Qbox related modules ********************
######    Adjust this block according to your needs ##########
module load qbox
#module unload mkl cuda openmpi
#module load intelmpi/2018.2.199+intel-18.0 mkl/2018.up2 xerces/3.1.4
qb=qb #/home/arpank/Qbox/bin/qb-1.71.0-eigval-prec-12

############################## Load distribution ######################################################
################        This is specific to midway @RCC UChicago         ##############################
################   adjust according to your cluster specifications       ############################## 
export I_MPI_PMI_LIBRARY=/software/slurm-current-el6-x86_64/lib/libpmi.so
export I_MPI_FABRICS=shm:dapl
export OMP_NUM_THREADS=1


################## Function to change total steps of i-pi input ###################################
##################      Required to setup dependency jobs       ####################################
##################        Do not touch anything here            ####################################
function insert_total_steps
{
if [[ $1 == *"RESTART"* ]] || [[ $1 == *"restart"* ]]; then
   echo "Provided i-pi input is a restart file."
   echo "Inserting: <total_steps>$2</total_steps>"
   if [ `grep -c '<total_steps>' $1` -ne 0 ]; then
      sed -i "/<total_steps>/c\   <total_steps>$2</total_steps>" $1
   else
      step_line_no=`grep -n '<step>' $1 |awk -F[:] '{print $1}'`
      sed -i "${step_line_no} a \   <total_steps>$2</total_steps>" $1
   fi
else
   echo "Provided i-pi input is not a restart file." 
   echo "Not changing the provided i-pi input."
fi
}

function insert_total_time
{
if [ `grep -c '<total_time>' $1` -ne 0 ]; then
      sed -i "/<total_time>/c\   <total_time>$2</total_time>" $1
else
      verbosity_line_no=`grep -n '<simulation verbosity' $1 |awk -F[:] '{print $1}'`
      sed -i "${verbosity_line_no} a \   <total_time>$2</total_time>" $1
fi
}

insert_total_time $ipi_input $total_time
insert_total_steps $ipi_input $total_steps

JOBID=`echo $SLURM_JOBID`
echo $SBATCH_PARTITION
echo $SBATCH_CONSTRAINT
cd $SLURM_SUBMIT_DIR


############################## Processor related variables ###########################################
############################## Do not touch this block     ###########################################
#echo "SLURM_NTASKS_PER_NODE= $SLURM_NTASKS_PER_NODE"
#echo "SLURM_JOB_NUM_NODES= $SLURM_JOB_NUM_NODES"
let NTASKS=$(($SLURM_NTASKS_PER_NODE * $SLURM_JOB_NUM_NODES))
#echo "NTASKS= $NTASKS"
let NCORE=${NTASKS}/${instance}
echo "NCORE= $NCORE"

let REMAINDER=${NCORE}%${SLURM_NTASKS_PER_NODE}

if [ "${REMAINDER}" -eq 0 ]; then
   let NUMNODES=${NCORE}/${SLURM_NTASKS_PER_NODE}
else
   let NUMNODES=${NCORE}/${SLURM_NTASKS_PER_NODE}+1
fi

echo "NUMNODES = $NUMNODES"

##############################     JOB SUBMISSIONS   ##################################################
#########################     Do not touch this block    ##############################################

#*********** i-PI job submission *******************
i-pi $ipi_input > $ipi_log 2>&1 &
sleep 10
error=`grep --ignore-case "error" $ipi_log | wc -l`  #error != 0 if ipi error occurs
if [ "$error" -ne 0 ]; then
   grep --ignore-case "error" $ipi_log
   exit
fi

#******* Qbox/Interface job submissions ************
num_nrowmax=`grep 'nrowmax' $qbox_initial | wc -l`   #if nrowmax specified it wont insert it
for i in `seq 1 ${instance}`
do
    mkdir instance_${i}
    cp $qbox_initial instance_${i}/${qbox_input}
    cd instance_${i}
    ### nrowmax insertion, deprecated in qbox
    #if [[ "$num_nrowmax" -eq 0 ]] && [[ "${NCORE}" -gt 32 ]]; then
    #   sed -i "1 i\ set nrowmax $NCORE" ${qbox_input}
    #fi
    srun --exclusive -N $NUMNODES -n $NCORE $qb $qb_opts -server $qbox_input $qbox_output > $qbox_log 2>&1 &
    $interface $SLURM_SUBMIT_DIR/$ipi_input $qbox_input $qbox_output > interface.log 2>&1 &
    cd ../
done

sleep 60

# checking if error occured and then exiting 
interface_path_error=0
for i in `seq 1 ${instance}`
do
    error_qbox=`grep "BAD TERMINATION" instance_${i}/$qbox_log | wc -l`
    error_interface=`grep --ignore-case "error" instance_${i}/interface.log | wc -l`
    let error=${error_qbox}+${error_interface}
    int_path_err=`grep --ignore-case "No such file or directory" instance_${i}/interface.log | wc -l`
    let interface_path_error=${interface_path_error}+${int_path_err}
done

function error_handler
{
         mkdir ${SLURM_JOB_NAME}.${JOBID}
         cp $ipi_log ${SLURM_JOB_NAME}.${JOBID}/ipi.log
         for i in `seq 1 ${instance}`
         do
             cp instance_${i}/$qbox_input ${SLURM_JOB_NAME}.${JOBID}/$qbox_input.$i
             cp instance_${i}/$qbox_output ${SLURM_JOB_NAME}.${JOBID}/$qbox_output.$i
             cp instance_${i}/interface.log ${SLURM_JOB_NAME}.${JOBID}/interface.log.${i}
             cp instance_${i}/${qbox_log} ${SLURM_JOB_NAME}.${JOBID}/${qbox_log}.${i}
             if [ -d instance_${i}/input_store ]; then
                mv instance_${i}/input_store ${SLURM_JOB_NAME}.${JOBID}/input_store.${i}
             fi
             if [ -d instance_${i}/output_store ]; then
                mv instance_${i}/output_store ${SLURM_JOB_NAME}.${JOBID}/output_store.${i}
             fi
             rm -rf instance_${i}
         done
         exit
}

qbin_path_error=`grep "No such file or directory" slurm-${JOBID}.out | wc -l`
path_error=0
if [ "$qbin_path_error" -ne 0 ]; then
   echo "Please correct the path for qbox_initial."
   let path_error=${path_error}+${qbin_path_error}
   #error_handler
fi

if [ "$interface_path_error" -ne 0 ]; then
   echo "Interface path is not correct. Either provide the full path or path relative to instance directories."
   let path_error=${path_error}+${interface_path_error}
   #error_handler
fi

if [ "$path_error" -ne 0 ]; then 
   error_handler
fi 


if [ "$error" -ne 0 ]; then
    echo "Error in qbox or interface."
    echo "Check $qbox_log or interface.log in directory: ${SLURM_JOB_NAME}.${JOBID}"
    error_handler
fi

##### checking runtime error if interface socket is disconnected
while  true; do
        dropped=`grep -c "died or got unresponsive(C). Removing from the list." $ipi_log`
        soft_exit=`grep -c "SIMULATION: Exiting cleanly." $ipi_log`
        if [ "$dropped" -gt 0 ]; then
           echo "Qbox interface dropped connection abruptly."
           echo "Check $qbox_log or interface.log in directory: ${SLURM_JOB_NAME}.${JOBID}"
           error_handler
        fi

        if [ "$soft_exit" -gt 0 ]; then
           break
        fi
        sleep 60
done


wait

############################ Collecting Qbox inputs/outputs in a file ################################
############################  Not needed to touch this function eitheer ##############################
#*********** Function to collect inputs and outputs********************************************** 
function collect_all 
{
no_ins=$1
store_dir_name=$2
work_dir=`pwd`
store_dir=${work_dir}/${store_dir_name}
mkdir $store_dir
         function collect_input
         {
         sufix=$1
         if [ -d input_store ]; then
               cd input_store
               cat input?.i input??.i input???.i input????.i input?????.i input??????.i input???????.i > ${store_dir}/inputs_${sufix}.i
               cd ../
         fi
         }

         function collect_output
         {
         sufix=$1
         if [ -d output_store ]; then
               cd output_store
               cat output?.r output??.r output???.r output????.r output?????.r output??????.r output???????.r > ${store_dir}/outputs_${sufix}.r
               cd ../
         fi
         }

for i in `seq 1 ${no_ins}`
do
    cd instance_${i}
    collect_input ${i}  &
    collect_output ${i} &
    cd $work_dir
done
wait
}
#************************************************************************************

### Collecting inputs and outputs
cd $SLURM_SUBMIT_DIR
collect_all ${instance} ${SLURM_JOB_NAME}.${JOBID}

for i in `seq 1 ${instance}`
do
    if [[ -d instance_${i}/cube_files ]]; then
       mv instance_${i}/cube_files ${SLURM_JOB_NAME}.${JOBID}/cube_files.${i}
    fi
    cp instance_${i}/interface.log ${SLURM_JOB_NAME}.${JOBID}/interface.log.${i}
    cp instance_${i}/${qbox_log} ${SLURM_JOB_NAME}.${JOBID}/${qbox_log}.${i} 
    #cp instance_${i}/last_sample.xml ${SLURM_JOB_NAME}.${JOBID}/last_sample.${i}.xml
done
#cp instance_1/last_sample.xml $SLURM_SUBMIT_DIR/qbox-init.xml   ### saving restart file
cp $ipi_log $ipi_input RESTART  ${SLURM_JOB_NAME}.${JOBID}/
rm -rf instance_*
echo "JOB DONE!!!"
echo "Check directory: ${SLURM_JOB_NAME}.${JOBID} for outputs and log files"

############  Archiving the results into long term storage ####################################
##### write copy command here to copy result files to project2
