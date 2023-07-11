#!/bin/bash

EXPERIMENT_ITERATIONS=10
SWAP_ITERATIONS=10

PROTOS=("TCP" "UDP")
DEV_INIT_MODES=("-fast-reconfig" "-hitless")
LEN_DEV_INIT_MODES=${#DEV_INIT_MODES[*]}
LEN_PROTOS=${#PROTOS[*]}

SWITCH_ADDRESS="<Switch IP Address>"
IPERF_SERVER="192.168.42.2" # VXLAN 42 address

IPERF_UDP_BITRATE="100M" # Neccessary because higher bitrates causes UDP bursts.

RETRY_COUNTER=3					# Retry times until iperf retry 

TIME_IPERF_RUN_CHECK=5			# Waiting time until iPerf should be up and running
TIME_AFTER_IPERF_START=4		# Waiting time until iPerf runs more time
TIME_BETWEEN_SWAPS=15			# Waiting time between code swaps
TIME_UNTIL_EXP_SHOULD_END=20 	# Additional time waiting until experiment should end and being cleaned up.
IPERF_EXTRA_TIME=1				# Additional time where iPerf should run
TIME_BETWEEN_EXPS=15			# Waiting time between each experiment iteration

P4_PROGRAM="tif"
SWAP_SCRIPT_PATH="~/working_space/"
SWAP_SCRIPT_PREFIX="swap_fwd_pipelineconf_$P4_PROGRAM"

EXPERIMENT_DATA_DIR="experiment_data/"
TIME_MEASUREMENT_EXPERIMENT_FILE_PREFIX="experiment-time-measurement-$P4_PROGRAM"
PREFIX_CSV_HEADERS="protocol,iteration,"

IPERF_DURATION=$(( TIME_IPERF_RUN_CHECK + TIME_AFTER_IPERF_START + TIME_BETWEEN_SWAPS * SWAP_ITERATIONS + TIME_UNTIL_EXP_SHOULD_END + IPERF_EXTRA_TIME ))

function get_unix_timestamp_in_secs () { echo "$(date +%s)"; }
function get_unix_timestamp_in_ms () { echo "$(date +%s%N | cut -b1-13)"; }
function get_unix_timestamp_in_ns () { echo "$(date +%s%N)"; }
function create_swap_csv_header() { echo "swap_$i\_start,swap_$i\_end"; }

function clean_up_timemeasurement_files () {
	# $1 --> Hostname
	echo "Cleanup time measurement files @ $1"
	ssh $1 "rm -f $HOME/time_measurement-*.csv"
}
function collect_data_from_host () {
	# $1 --> Hostname
	rsync --progress $1:"$HOME/time_measurement-*.csv" $HOME/experiments/$EXPERIMENT_DATA_DIR/
	retval=$?
	if [ $retval -eq 0 ]
	then
		clean_up_timemeasurement_files $1
	fi
}
function save_timemeasurement_of_experiment () {
	# $1 --> $Dev_Init_Mode
    # $2 --> $CSV_HEADERS
    # $3 --> $CSV_DATA_ROW
	FILE="$EXPERIMENT_DATA_DIR/$TIME_MEASUREMENT_EXPERIMENT_FILE_PREFIX$1.csv"
    if [ ! -f "$FILE" ]; then
        echo "$2" > $FILE
    fi
    echo "$3" >> $FILE
}

swap_csv_header=""
for (( i = 1; i <= SWAP_ITERATIONS; i++ ))
do
	if [ "$i" == 1 ]
	then
		swap_csv_header=$(create_swap_csv_header $i)
	else
		swap_csv_header="$swap_csv_header,$(create_swap_csv_header $i)"
	fi
done

CSV_HEADERS="$PREFIX_CSV_HEADERS,$swap_csv_header"

mkdir -p $EXPERIMENT_DATA_DIR

printf "IPERF Duration:\t\t $IPERF_DURATION\n"
printf "Experiment Iterations:\t $EXPERIMENT_ITERATIONS\n"
printf "Swap Iterations:\t $SWAP_ITERATIONS\n"
printf "Protos:\t\t\t %s\n" "${PROTOS[*]}"
printf "Device Init Modes:\t %s\n" "${DEV_INIT_MODES[*]}"
printf "\n*******************************************************************************************\n"
printf "***\t One Experiment takes ~ $(( IPERF_DURATION + TIME_IPERF_RUN_CHECK )) secs\t\t\t\t\t\t\t*** \n"
printf "***\t --> All Iterations of one mode takes ~ $(( (IPERF_DURATION + TIME_IPERF_RUN_CHECK) * EXPERIMENT_ITERATIONS )) secs ($(( ((IPERF_DURATION + TIME_IPERF_RUN_CHECK) * EXPERIMENT_ITERATIONS) / 60 )) mins)\t\t\t*** \n"
printf "*** \t --> All Modes takes ~ $(( (IPERF_DURATION + TIME_IPERF_RUN_CHECK) * EXPERIMENT_ITERATIONS * LEN_PROTOS * LEN_DEV_INIT_MODES )) secs ($(( ((IPERF_DURATION + TIME_IPERF_RUN_CHECK) * EXPERIMENT_ITERATIONS * LEN_PROTOS * LEN_DEV_INIT_MODES) / 60 )) mins)\t\t\t\t\t***\n"
printf "*** \t --> All in all (including time between exps) takes ~ $(( (IPERF_DURATION + TIME_IPERF_RUN_CHECK + TIME_BETWEEN_EXPS) * EXPERIMENT_ITERATIONS * LEN_PROTOS * LEN_DEV_INIT_MODES )) secs ($(( ((IPERF_DURATION + TIME_IPERF_RUN_CHECK + TIME_BETWEEN_EXPS) * EXPERIMENT_ITERATIONS * LEN_PROTOS * LEN_DEV_INIT_MODES) / 60 )) mins)\t***"
printf "\n*******************************************************************************************\n"

for proto in "${PROTOS[@]}"
do
	for dim in "${DEV_INIT_MODES[@]}"
	do
		SWAP_SCRIPT="$SWAP_SCRIPT_PATH$SWAP_SCRIPT_PREFIX$dim"
		printf "swap script: $SWAP_SCRIPT \n"
		for ((i = 1; i <= EXPERIMENT_ITERATIONS; i++))
		do
			echo "---------------------------------------------------------------------------"
			echo "Run Experiment Iteration $i ($proto)"
			if [ "$proto" == "TCP" ]
			then
				echo "Starting Iperf3 in TCP for $IPERF_DURATION secs (DIM: $dim)"
				iperf3 -c $IPERF_SERVER -t $IPERF_DURATION -J 2&>1 > $EXPERIMENT_DATA_DIR/iperf-c-$P4_PROGRAM-$i$dim.json &
				counter=0
				sleep $TIME_IPERF_RUN_CHECK
				iperf_rt=$?
				echo "IPerf Process status: $iperf_rt"
				while ((iperf_rt != 0 && counter < RETRY_COUNTER)) ;
				do
						echo "Iperf3 not running - Try again... ($counter time tried)"
						echo "Starting Iperf3 in $proto for $IPERF_DURATION secs (DIM: $dim)"
						iperf3 -c $IPERF_SERVER -t $IPERF_DURATION -J 2&>1 > $EXPERIMENT_DATA_DIR/iperf-c-$P4_PROGRAM-$i$dim.json &
						((counter++))
				done
				if [ "$iperf_rt" != 0 ]
				then
					echo "Iperf retries count exceeded. Terminate Experiment."
					exit 1
				fi
			fi
			if [ "$proto" == "UDP" ]
			then
				echo "Starting Iperf3 in $proto for $IPERF_DURATION secs (DIM: $dim)"
				iperf3 -c $IPERF_SERVER -R -b $IPERF_UDP_BITRATE -t $IPERF_DURATION -u -J 2&>1 > $EXPERIMENT_DATA_DIR/iperf-c-$P4_PROGRAM-$proto-$i$dim.json &
				counter=0
				sleep $TIME_IPERF_RUN_CHECK
				iperf_rt=$(( $? ))
				echo "IPerf Process status: $iperf_rt"
				while ((iperf_rt != 0 && counter < RETRY_COUNTER))
				do
						echo "Iperf3 not running - Try again... ($counter time tried)"
						echo "Starting Iperf3 in $proto for $IPERF_DURATION secs (DIM: $dim)"
						iperf3 -c $IPERF_SERVER -R -b $IPERF_UDP_BITRATE -t $IPERF_DURATION -u -J 2&>1 > $EXPERIMENT_DATA_DIR/iperf-c-$P4_PROGRAM-$proto-$i$dim.json &
						((counter++))
				done
				if [ "$iperf_rt" != 0 ]
				then
					echo "Iperf retries count exceeded. Terminate Experiment."
					exit 1
				fi
			fi
			sleep $TIME_AFTER_IPERF_START
			swap_time=""
			for ((j=1; j <= SWAP_ITERATIONS; j++))
			do
				echo Swap Iteration $j
				SWAP_START="$(get_unix_timestamp_in_ms)"
				ssh $SWITCH_ADDRESS $SWAP_SCRIPT $proto $i $j
				SWAP_END="$(get_unix_timestamp_in_ms)"
				if [ "$j" == 1 ]
				then
					swap_time="$SWAP_START,$SWAP_END"
				else
					swap_time="$swap_time,$SWAP_START,$SWAP_END"
				fi
				CALC_TIME_BETWEEN_SWAPS=$(echo "$TIME_BETWEEN_SWAPS - ($SWAP_END / 1000 - $SWAP_START / 1000)" | bc)
				# echo $CALC_TIME_BETWEEN_SWAPS
				sleep $CALC_TIME_BETWEEN_SWAPS
			done
			sleep $TIME_UNTIL_EXP_SHOULD_END
			echo "Waiting some more time ($TIME_BETWEEN_EXPS secs)"
			sleep $TIME_BETWEEN_EXPS
			
			echo "Save Time Measurement for this experiment to file..."
			CSV_DATA_ROW="$proto,$i,$swap_time"
			save_timemeasurement_of_experiment $dim $CSV_HEADERS $CSV_DATA_ROW
		done
	done
done

collect_data_from_host $SWITCH_ADDRESS