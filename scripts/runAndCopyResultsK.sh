#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo "Error: Needs 1 arg: copy dest folder"
    exit
fi

dd=$1

apptainer exec -B /media/bj48 $tp/singularity/yade/debian-trixie.sif yade -j1 -n -x simWheelSoilBoxKyoto.py 2> log2 > log

mkdir -p $dd
cp -p simWheelSoilBoxKyoto.py $dd
mv plot_end.txt plot_end.pdf Data_Output.csv calltime_PIDrotate_tractionF_4.9N.txt log log2 $dd
rm save_1s.bz2 save_2s.bz2
