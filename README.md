# TIF Experiments

This repository contains experiments used for evaluation of the bandwidth measurement for a simple switch reconfiguration code implementing a repeater, and a TIF switch reconfiguration code.

It is part of the paper ```Low Impact Tenant Code Updates on Multi-tenant Programmable Switches```.

## Disclaimer

> This repositories contains code which was using proprietary hardware and software. 
> Due to their license, these code parts were removed and must be added again, or triggered manually to achieve the experiment setup used in the proposed paper!

## Prerequisites

- iPerf3 must be installed on both used hosts.
- The experiments were done with Tofino 1 switch, where the chip was started and initialized with the Barefoot SDE.
- You need to compile the test code properly. 
    - See for a example repeater implementation this [P4 code](https://github.com/prona-p4-learning-platform/p4-boilerplate/blob/main/Example1-Repeater/tna/pronarepeater.p4)
    - To get a working TIF forwarding pipeline config example, you can compile the given initial TIF by the SDE compiler or save the TIF compiled by [OMuProCU-core](https://github.com/tiritor/OMuProCU-core). 
- Because of the license, some parts (e.g., Hardware initialization) in the *experiment and swap scripts* are **removed**. This must be added again to get this repository into a working state again.
- Also, the swap scripts and the test code must be available at the Tofino 1 switch.

## Usage

There are two experiment scripts which were used for this evaluation in the mentioned paper.

### [experiment.sh](experiment.sh)

This script will start a experiment running iPerf3 for the defined duration while it will trigger a switch reconfiguration and hardware initialization every 10 seconds. 
This experiment will repeated 10 times to achieve a significant result.

### [experiment-tif.sh](experiment-tif.sh)

This script do the same as described [before](#experimentsh), with the only difference that a TIF example is used as switch chip reconfiguration code.


## Evaluation

The evaluation script used for the postprocessing of the experiment is also available in this repository.

It is recommended to create a python virtual environment and install the needed python packages into it. 


```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

Afterwards, when the experiments were run successfully, you can the following command to generate plots and tables:

```
python3 experiments-post-processing.py
```