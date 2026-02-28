#!/usr/bin/env bash

if [ -z "$2" ]; then
    echo "Error: Needs 2 args: param filename & copy dest folder"
    exit
fi

pf=$1
dd=$2
shift 2

apptainer exec -B /media/bj48 $tp/singularity/yade/debian-trixie.sif yade -j1 -n -x simWheelSoilBox.py $pf $@ 2> log2 > log

mkdir -p $dd
cp -p simWheelSoilBox.py $pf $dd
mv plot.txt plot.pdf Data_Output.csv exec_time.txt log log2 $dd
