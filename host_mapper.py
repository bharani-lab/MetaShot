__author__ = 'Bruno Fosso'
__version__ = "1.0"

import getopt
import os
import shlex
import shutil
import sys
from string import strip
import psutil
from pysam import Samfile


def usage():
    print ('This script maps the non microbial sequences on the host genome and trascriptome:\n'
           '\t-i    paired-end file list: a line containing the R1, the R2 files\n'
           '\t-s    host species. Available species are Homo sapiens (human) and Mus musculus (mouse) [DEFAULT human]\n'
           '\t-r\treference path [MANDATORY]\n'
           '\t-g    Preloaded genome: if the genome is preloaded please insert this option\n'
           '\t-h    print this help.\n'
           'Usage:\n'
           '\tpython human_mapper.py -s human -i read_list\n'
           '\t')


f_in = ""
host = "human"
genome = ""
reference_path = ""
try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:s:r:g")
except getopt.GetoptError, err:
    print str(err)
    usage()
    sys.exit()
if len(opts) != 0:
    for o, a in opts:
        if o == "-h":
            usage()
            sys.exit()
        elif o == "-i":
            f_in = a
        elif o == "-s":
            host = a.replace(" ", "_")
        elif o == "-r":
            reference_path = a
        elif o == "-g":
            genome = "--genomeLoad LoadAndKeep"
        else:
            usage()
            exit()
else:
    usage()
    exit()


def verify_input_data(aa, b):
    print """
    Prior to the data analysis the input data are checked
    """
    if len(aa) == 0:
        print "forward read file list is empty"
        usage()
        exit()
    if len(b) == 0:
        print "reverds read file list is empty"
        usage()
        exit()


if reference_path == "":
    sys.exit("No reference_path is indicated")

reference_STAR = {"human": {"genome": os.path.join(reference_path, "Homo_sapiens")}}


def controllo_read_file(l):
    if os.path.exists(l):
        campi = open(l).readlines()[0].split("\t")
        if len(campi) == 2:
            print "correctly formatted read_list file"
        else:
            print "uncorrectly formatted read_list file"
            exit()
    else:
        print "read-file doesn't exist"
        usage()
        exit()


controllo_read_file(f_in)

R1 = ""
R2 = ""
for line in open(f_in):
    s = map(strip, line.split("\t"))
    R1 = s[0]
    R2 = s[1]


def define_correct_host_name(species):
    synonyms = {"human": ["Homo sapiens", "homo", "human"]}
    for host_key in synonyms.keys():
        if species.lower() in synonyms[host_key]:
            return host_key


host = define_correct_host_name(host)
if host is None:
    print "UNCORRECT HOST SPECIES"
    sys.exit()

wd = os.getcwd()
folder = os.path.join(wd, "mapping_on_" + host)
if os.path.exists(folder) is False:
    os.mkdir(folder)


def controll_mapping_procedure(sam_file):
    if os.path.exists(sam_file) and os.stat(sam_file)[6] != 0:
        try:
            controllo_sam = Samfile(os.path.join(sam_file))
            controllo_sam.close()
            align_result = 1
        except:
            align_result = 0
    else:
        align_result = 0
    return align_result


def choice_reference(species, ref_genome):
    """
    :type ref_genome: str
    :type species: str
    """
    if species in reference_STAR.keys():
        return reference_STAR[species][ref_genome]
    else:
        print "UNCORRECT HOST SPECIES"
        usage()
        sys.exit()


R1 = os.path.join(wd, R1)
R2 = os.path.join(wd, R2)
print "Mapping on the genome"
os.chdir(folder)
genome_database = choice_reference(host, "genome")
cmd = shlex.split(
    "STAR --runThreadN 10 --genomeDir %s %s --readFilesIn %s %s --outSAMattributes NM --alignIntronMax 1000000 "
    "--alignIntronMin 1  --outFileNamePrefix %s_data" % ( 
        os.path.join(reference_path, "Homo_sapiens/"), genome, R1, R2, host))
p = psutil.Popen(cmd)
p.wait()
os.chdir(wd)

control_sam = os.path.join(folder, host + "_dataAligned.out.sam")
r1_mapped = set()
r2_mapped = set()

print "sam parsing"
result = controll_mapping_procedure(control_sam)
if result == 0:
    print "The sam file " + control_sam + " is not correctly created....repeat the script execution"
    shutil.rmtree(folder)
    sys.exit()
elif result >= 1:
    sam = Samfile(control_sam)
    for align in sam.fetch(until_eof=True):
        if align.tid != -1:
            query_name = align.qname  # accession della read
            query_len = float(align.rlen)  # lunghezza delle read in esame
            threshold = int((query_len / 100) * 3) + 1
            if align.cigar is not None:
                nm = -1
                for coppia in align.tags:
                    if coppia[0] == "NM":
                        nm = float(coppia[1])
                if 0 <= nm <= threshold:
                    if align.is_read1:
                        r1_mapped.add(query_name)
                    elif align.is_read2:
                        r2_mapped.add(query_name)
    sam.close()

human_mapped = r1_mapped.intersection(r2_mapped)
tmp = open(os.path.join(folder, "mapped_on_host.lst"), "w")
for acc in human_mapped:
    tmp.write("%s\n" % acc)
tmp.close()

print "HOST MAPPING IS DONE"
