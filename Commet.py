# Contributors :
#   Pierre PETERLONGO, pierre.peterlongo@inria.fr [12/06/13]
#   Nicolas MAILLET, nicolas.maillet@inria.fr     [12/06/13]
#   Guillaume Collet, guillaume@gcollet.fr        [27/05/14]
#
# This software is a computer program whose purpose is to find all the
# similar reads between two set of NGS reads. It also provide a similarity
# score between the two samples.
#
# Copyright (C) 2014  INRIA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import errno
import random
import string
import argparse
import subprocess




##############################################################################################################
#################### From a file of files - store in an array the read files           #######################
#################### A line = a set of read sets composing the same viratual dataset   #######################
#################### A line per input virtual dataset                                  #######################
##############################################################################################################
def getReadFiles(F):
    matrix= []
    fofs=open(F,'r')
    while(True):
        line=fofs.readline()
        if not line: break
        line=line.split(":")[1]
        tab_line=line[:-1].split(";") # [:-1] removes the \n
        for i in range(len(tab_line)):
            tab_line[i]=tab_line[i].strip() # removes first and/or last empty characters before and after set names
        matrix.append(tab_line)
    fofs.close()
    return matrix
    
def getReadSetsNames(F):
    table= []
    fofs=open(F,'r')
    while(True):
        line=fofs.readline()
        if not line: break
        table.append(line.split(":")[0].strip())
    return table
    

##############################################################################################################
#################### From  an array of the read files                                  #######################
#################### Filter the reads respecting parameters                            #######################
#################### For each set generates a .bv having the same name as the input read set #################
##############################################################################################################   
def filterAllReads(readSetMatrix, output_directory, l, n, e, m, SGE_COMMANDS):
    options=" -l "+str(l)+" -e "+str(e)
    filtering_job_ids=""
    if(n>=0):
        options+=" -n "+str(n)
    for tab_line in readSetMatrix:
        m_option=""
        if m>=0:
            local_m=m/len(tab_line)
            m_option=" -m "+str(local_m)
        for i in range(len(tab_line)):
            command="./filter_reads "+tab_line[i]+options+m_option+" -o "+output_directory+os.path.basename(tab_line[i])+".bv"
            print "Filtering command: "+command
            if not SGE_COMMANDS:
                os.system(command)
            else:
		filtering_job_ids+=os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -N filter").read().split(" ")[2]
                filtering_job_ids+=","
    return filtering_job_ids[:-1]

##############################################################################################################
#################### For each read set: generates a file containing the original line + the .bv info   #######
##############################################################################################################
def generateAFileOfFilesPerOriginalWithFilterBooleanVector(readSetMatrix, readSetNames, output_directory, temp_files_prefix):
    line_id=0
    for tab_line in readSetMatrix:
        per_set_fofs_bv=open(readSetNames[line_id]+"_"+temp_files_prefix+".txt",'w')
        per_set_fofs_bv.write(readSetNames[line_id]+":")
        line_id+=1
        for i in range(len(tab_line)):
            per_set_fofs_bv.write(tab_line[i]+","+output_directory+os.path.basename(tab_line[i])+".bv")
            if i<len(tab_line)-1: 
                per_set_fofs_bv.write(";")
        per_set_fofs_bv.close()
        
        
##############################################################################################################
####################    #######
##############################################################################################################
def generate_A_File_Of_File_Index_WRT_A_Set(readSetMatrix, readSetNames, output_directory, FileName, previous_ref_id, current_index_id):
    line_id=0
    file=open(FileName,'w')
    file.write(readSetNames[current_index_id]+":")
    tab_line=readSetMatrix[current_index_id]
    for i in range(len(tab_line)):
        file.write(tab_line[i]+","+output_directory+os.path.basename(tab_line[i])+"_in_"+os.path.basename(readSetNames[previous_ref_id])+".bv")
        if i<len(tab_line)-1:
            file.write(";")            
    file.close()
        
        

##############################################################################################################
#################### For each index: generates the query file of files                       #################
##############################################################################################################
def generateAFileOfSetOfFilesOriginalWithFilterBooleanVector(readSetMatrix, readSetNames, output_directory, fileName, whichToIndex):
    line_id=0
    index_fofs_bv=open(fileName,'w') #
    for line_id in range(whichToIndex):
        tab_line=readSetMatrix[line_id]
        index_fofs_bv.write(readSetNames[line_id]+":")
        for i in range(len(tab_line)):
            index_fofs_bv.write(tab_line[i]+","+output_directory+os.path.basename(tab_line[i])+".bv")
            if i<len(tab_line)-1: 
                index_fofs_bv.write(";")
        index_fofs_bv.write("\n")
    index_fofs_bv.close()
    

            

##############################################################################################################
#################### Compare all read sets against a reference file and then                 #################
#################### And finish symetrical comparisons                                       #################
##############################################################################################################
def compare_all_against(readSetMatrix, readSetNames, output_directory, temp_files_prefix, index_reference_set, k, t, SGE_COMMANDS, filtering_job_ids):
    
    kt_options=" -t "+str(t)+" -k "+str(k)+" "
    
    ########### PART all in Si ############
    
    # Launch ref against all others. Grab the job id what will be used for waiting for the end of this step 
    # Does the job A in Sindex and B in Sindex and C in Sindex (with Sindex is the line pointed by index_reference_set in the file temp_files_prefix+"_BV_filters.txt)
    # for each Si in [0,index_reference_set-1]  the output is a set of file of files set_i_in_Xj.txt (with j = index_reference_set) per i in [0,index_reference_set]
    queries_fof_file_name="queries_for_index_"+readSetNames[index_reference_set]+"_"+temp_files_prefix+".txt"
    generateAFileOfSetOfFilesOriginalWithFilterBooleanVector(readSetMatrix, readSetNames, output_directory, queries_fof_file_name, index_reference_set)
    index_fof_file_name=readSetNames[index_reference_set]+"_"+temp_files_prefix+".txt"
    command="./index_and_search -i "+index_fof_file_name + " -s "+queries_fof_file_name+ " -o "+output_directory+kt_options
    last_job_ids=""
    print "All in "+ readSetNames[index_reference_set]+": Command="+command
    ref_job_id=""
    if SGE_COMMANDS:
        ref_job_id=int(os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -hold_jid "+str(filtering_job_ids)+" -N \"log_all_in_"+str(index_reference_set)+"\"").read().split(" ")[2])
    else:
        os.popen(command)
    
    # for each couple: Si, X : X in (Si in X)
    for i in range(index_reference_set):
        # PART Si_in_X
    
        
        # Computes X in (Si in X)
        #########################
        index_file_name="index_"+readSetNames[i]+"_previous_"+readSetNames[index_reference_set]+"_"+temp_files_prefix+".txt"
        generate_A_File_Of_File_Index_WRT_A_Set(readSetMatrix, readSetNames, output_directory, index_file_name, index_reference_set, i)
        query_file_name=readSetNames[index_reference_set]+"_"+temp_files_prefix+".txt"
        command="./index_and_search -i "+index_file_name+" -s "+query_file_name+ " -o "+output_directory+kt_options
        print " "+readSetNames[index_reference_set]+" in ("+ readSetNames[i]+" in "+readSetNames[index_reference_set]+"): Command="+command
        X_in_Si_job_id=""
        if SGE_COMMANDS:
            X_in_Si_job_id=os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -hold_jid "+str(ref_job_id)+" -N \"log_"+str(index_reference_set)+"_in_"+str(i)+"\"").read().split(" ")[2]
        else:
            os.popen(command)
        
        # Computes Si in (X in (Si in X))
        #################################
        index_file_name="index_"+readSetNames[index_reference_set]+"_previous_"+readSetNames[i]+"_"+temp_files_prefix+".txt"
        generate_A_File_Of_File_Index_WRT_A_Set(readSetMatrix, readSetNames, output_directory, index_file_name, i, index_reference_set)
        query_file_name=readSetNames[i]+"_"+temp_files_prefix+".txt"
        command="./index_and_search -i "+index_file_name+" -s "+query_file_name+ " -o "+output_directory+kt_options
        print " "+readSetNames[i]+"_in_("+readSetNames[index_reference_set]+" in ("+ readSetNames[i]+" in "+readSetNames[index_reference_set]+")): Command="+command
        if SGE_COMMANDS:
            last_job_ids+=os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -hold_jid "+str(X_in_Si_job_id)+" -N \"log_"+str(i)+"_in_"+str(index_reference_set)+"\"").read().split(" ")[2]+","
        else:
            os.popen(command)
        
        
    return last_job_ids

##############################################################################################################
#################### Output the results matrix (csv)                                         #################
##############################################################################################################
def output_matrices (readSetMatrix, readSetNames, output_directory, matrix_prefix):
    matrix_sum_shared_reads=[] # for each set, number of shared reads with each other sets [Matrix]
    number_reads_all_sets=[] # for each set, number of considered reads
    max_plain=0
    max_plain_diag=0
    max_percentage=0
    max_normalized=0
    
    # Fill the matrices
    ####################
    for id_set in range(len(readSetNames)):
        # detect the number of involved reads per line of the input
        number_reads=0
        for read_set in readSetMatrix[id_set]:
            command="./bvop "+output_directory+os.path.basename(read_set)+".bv -i"
            #print command
            number_reads+=int(os.popen(command).read().split("\n")[-2].split()[0])
        number_reads_all_sets.append(number_reads)
        
        # detect the number of shared reads with all other sets:
        array_sum_shared_reads=[]
        for id_target_set in range(len(readSetNames)): # for each target set
            if id_set == id_target_set:
                array_sum_shared_reads.append(number_reads_all_sets[id_set])
                continue;
            number_shared_reads=0
            for read_set in readSetMatrix[id_set]: # for each read set of the surrent set of read sets :)
                command="./bvop "+output_directory+os.path.basename(read_set)+"_in_"+readSetNames[id_target_set]+".bv -i"
		number_shared_reads+=int(os.popen(command).read().split("\n")[-2].split()[0]) # get the  number of shared reads
            array_sum_shared_reads.append(number_shared_reads)
        matrix_sum_shared_reads.append(array_sum_shared_reads)
    
    
    
    # Print the matrices
    #####################
    # Plain Matrix
    matrix_file=open(output_directory+matrix_prefix+"_plain.csv","w")
        
    for set_name in readSetNames:
        matrix_file.write(";"+set_name)
    matrix_file.write("\n")
    for id_set in range(len(readSetNames)):
        matrix_file.write(readSetNames[id_set])
        for id_target_set in range(len(readSetNames)):
            if id_target_set!=id_set and matrix_sum_shared_reads[id_set][id_target_set] > max_plain: max_plain = matrix_sum_shared_reads[id_set][id_target_set]
            if id_target_set==id_set and matrix_sum_shared_reads[id_set][id_target_set] > max_plain_diag: max_plain_diag = matrix_sum_shared_reads[id_set][id_target_set]
            matrix_file.write(";"+str(matrix_sum_shared_reads[id_set][id_target_set]))
            
        matrix_file.write("\n")
    if matrix_prefix: matrix_file.close()
    
    # Percentage matrix:
    matrix_file=open(output_directory+matrix_prefix+"_percentage.csv","w")
    for set_name in readSetNames:
        matrix_file.write(";"+set_name)
    matrix_file.write("\n")
    for id_set in range(len(readSetNames)):
        matrix_file.write(readSetNames[id_set])
        for id_target_set in range(len(readSetNames)):
            value=100*matrix_sum_shared_reads[id_set][id_target_set]/float(number_reads_all_sets[id_set])
            if id_target_set!=id_set and value > max_percentage: max_percentage=value
            matrix_file.write(";"+str(value))
        matrix_file.write("\n")
    if matrix_prefix: matrix_file.close()
    
    
    
    # Normalized matrix:
    matrix_file=open(output_directory+matrix_prefix+"_normalized.csv","w")
    for set_name in readSetNames:
        matrix_file.write(";"+set_name)
    matrix_file.write("\n")
    for id_set in range(len(readSetNames)):
        matrix_file.write(readSetNames[id_set])
        for id_target_set in range(len(readSetNames)):
            value=100*(matrix_sum_shared_reads[id_set][id_target_set]+matrix_sum_shared_reads[id_target_set][id_set])/float(number_reads_all_sets[id_set]+number_reads_all_sets[id_target_set])
            if id_target_set!=id_set and value > max_normalized: max_normalized=value
            matrix_file.write(";"+str(value))
        matrix_file.write("\n")
    if matrix_prefix: matrix_file.close()
    
    
    # Plot the dendrograms (only if a matrix file was given)
    ########################################################
    # Plain Matrix
    command="Rscript --vanilla dendro.R "+output_directory+matrix_prefix+"_plain.csv " + str(len(readSetNames))+ " " +output_directory+matrix_prefix+"_plain.pdf"
    print command
    os.system(command)
    # Percentage matrix:
    command="Rscript --vanilla dendro.R "+output_directory+matrix_prefix+"_percentage.csv " +str(len(readSetNames))+ " " +output_directory+matrix_prefix+"_percentage.pdf"
    os.system(command)
    # Normalized matrix:
    command="Rscript --vanilla dendro.R "+output_directory+matrix_prefix+"_normalized.csv " +str(len(readSetNames))+ " " +output_directory+matrix_prefix+"_normalized.pdf"
    os.system(command)
    
    
    # Plot the heatmap matrices
    # Plain Matrix
    command="Rscript --vanilla heatmap.r "+output_directory+matrix_prefix+"_plain.csv " + output_directory+matrix_prefix+"_plain_heatmap.pdf " + str(max_plain) + " " + str(max_plain_diag)+ " "+ matrix_prefix+"_plain"
    os.system(command)
    # Percentage Matrix
    command="Rscript --vanilla heatmap.r "+output_directory+matrix_prefix+"_percentage.csv " + output_directory+matrix_prefix+"_percentage_heatmap.pdf " + str(max_percentage) + " 100 " + matrix_prefix+"_percentage"
    os.system(command)
    # Normalized Matrix
    command="Rscript --vanilla heatmap.r "+output_directory+matrix_prefix+"_normalized.csv " + output_directory+matrix_prefix+"_normalized_heatmap.pdf " + str(max_normalized) + " 100 " + matrix_prefix+"_normalized"
    print command
    os.system(command)
    
##############################################################################################################
#################### Calling functions                                                       #################
##############################################################################################################   

def main():
    parser = argparse.ArgumentParser(description='Computes the filtering and the full N time N intersections of read sets')
    parser.add_argument("input_file", type=str,
                        help="input file of files (a line=a set composed by: \"set_name:read_file;read_file;read_file...\")" )
                        
    parser.add_argument('--sge', help='indicates the usage of SGE cluster commands', action="store_true") # SGE 
    
    parser.add_argument("-o", "--output_directory", type=str, dest='directory', metavar='',
                        help="directory in which vector results will be output [default: \"output_commet\"]", default="output_commet/" )
                        
    parser.add_argument("-k", type=int, dest='k', 
                        help="kmer size [default: 32]", default=32 )
                        
    parser.add_argument("-t", type=int, dest='t',
                        help="Minimal number of shared k-mers [default: 2]", default=2 )
    
    parser.add_argument("-l", type=int, dest='l',
                        help=" minimal length a read should have to be kept [default=0]", default=0 )
   
    parser.add_argument("-n", type=int, dest='n',
                        help="maximal number of Ns a read should contain to be kept. [default=any]", default=-1 )
 
    parser.add_argument("-e", type=float, dest='e',
                        help="minimal Shannon index a read should have to be kept. Float in [0,2]. [default=0]", default=0 )
    
    parser.add_argument("-m", type=int, dest='m',
                        help="maximum number of selected reads - This applies to a full set of reads. If a line of input_file is composed by 3 read files, and m=600, then the first 200 reads from each read file will be treated. [default=all]", default=-1 )
    
    parser.add_argument("prefix_matrix", type=str,
                        help="prefix of files in which matrices are output (in the output directory)[default=stdout]", default=None)
    

    args = parser.parse_args()
 
    # The input file of files
    input_file=str(args.input_file)
    output_directory=str(args.directory)+"/"
    output_matrix_prefix=args.prefix_matrix
    k=args.k
    t=args.t
    l=args.l
    n=args.n
    e=args.e
    m=args.m

    print "input file="+input_file, 
    

    #ouput directory
    print " output directory="+output_directory
    try:
        os.makedirs(output_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    print "output matrices prefix: in:"+output_matrix_prefix


    print "k="+str(k), 
    
    print " t="+str(t),
    
    print " l="+str(l),
    
    if(n>=0):
        print " n="+str(n),
    else:
        print " n=any",
    
    
    print " e="+str(e), 
    
    if(m>=0):
        print "m="+str(m)
    else:
        print "m=all"
        
    SGE_COMMANDS=False
    if args.sge: 
        print "SGE mode turned on"
        SGE_COMMANDS=True
        
    
    # Generate a temp prefix file name
    temp_files_prefix="temp_"
    for i in range(20): temp_files_prefix+=random.choice(string.ascii_letters)

    # Stores the input reads in a matrix
    readSetMatrix = getReadFiles(input_file)
    readSetNames = getReadSetsNames(input_file)
    
    # Filter the reads 
    filtering_job_ids=filterAllReads(readSetMatrix, output_directory, l, n, e, m, SGE_COMMANDS)
    
    # Generate the file of files containing the .bv of the filtered reads
    generateAFileOfFilesPerOriginalWithFilterBooleanVector(readSetMatrix, readSetNames, output_directory, temp_files_prefix)
    
    # Compare all against all
    alljobids=""
    for ref_id in range(len(readSetMatrix)-1,0,-1):
        jobids=compare_all_against(readSetMatrix, readSetNames, output_directory, temp_files_prefix, ref_id, k, t, SGE_COMMANDS, filtering_job_ids)
        alljobids+=jobids
    
    if not SGE_COMMANDS:
        output_matrices (readSetMatrix, readSetNames, output_directory, output_matrix_prefix)
        
    alljobids=alljobids[:-1] # remove the last ','
    if SGE_COMMANDS:
        command="rm -f *"+temp_files_prefix+"*"
        os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -hold_jid "+str(alljobids)+" -N \"clean\"")
        command="source /softs/local/env/envR.sh;  . /softs/local/env/envpython-2.7.sh ; ./Commet_analysis.py "+input_file+" "+output_matrix_prefix+" -o "+output_directory
        last_job_id=int(os.popen("echo \""+command+"\"| qsub -cwd -m beas -j y -hold_jid "+str(alljobids)+" -N \"make_matrices\"").read().split(" ")[2])
        print "All Commet jobs are launched - once last job ("+str(last_job_id)+") is over, all output matrices will be in:"
        print 
    else:
        os.popen("rm -f *"+temp_files_prefix+"*")
	print "All Commet work is done"
    print "\t Output csv matrices are in:"        
    print "\t\t"+output_directory+output_matrix_prefix+"_plain.csv"
    print "\t\t"+output_directory+output_matrix_prefix+"_percentage.csv"
    print "\t\t"+output_directory+output_matrix_prefix+"_normalized.csv"
    print "\t Output pdf dendrograms are in:"       
    print "\t\t"+output_directory+output_matrix_prefix+"_plain.pdf"
    print "\t\t"+output_directory+output_matrix_prefix+"_percentage.pdf"
    print "\t\t"+output_directory+output_matrix_prefix+"_normalized.pdf"
    print "\t Output pdf heatmaps are in:"       
    print "\t\t"+output_directory+output_matrix_prefix+"_plain_heatmap.pdf"
    print "\t\t"+output_directory+output_matrix_prefix+"_percentage_heatmap.pdf"
    print "\t\t"+output_directory+output_matrix_prefix+"_normalized_heatmap.pdf"
    

if __name__ == "__main__":
    main()
        
 











