#!/usr/bin/python3

import json
import logging
import sys
import matplotlib.pyplot as plt
import pandas as pd

INTERVAL = 0.1 # in secs
REMOVE_FROM_SOURCE_PATH = False

logger = logging.getLogger("TIF-Swap-PP")
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

KBits = 10 ** 3
Mbits = 10 ** 6
BitsUnit = Mbits

experiment_proto = {}

#### NEW DATA FORMAT 
MODES = { 
    "-fast-reconfig": {"iterations" : 10, "export_interval": 1},
    "-hitless": {"iterations" : 10, "export_interval": 1}
}

P4CODE = [
    "pronarepeater",
    "tif"
]

experiment_data_source_path = "experiment_data/PAPER/"

plt.rcParams["figure.autolayout"] = True


def create_connection_line(log_filename, mode, p4code="", iterations=None):
    """
    Collect all needed data for the evaluation of one iPerf run.
    """
    bps = []
    retransmits = []
    protocol = None
    target_bitrate = 0.0
    target_ip = ""
    if iterations == None:
        with open(experiment_data_source_path + log_filename.format(p4code, mode), "r") as f:
            iperf_log = json.load(f)
            for key, object in iperf_log.items():
                if "start" == key:
                    if "test_start" in object.keys():
                        # FIXME: This should be impossible @ experiments!
                        continue
                    protocol = object["test_start"]["protocol"]
                    target_ip = object["connected"][0]["remote_host"]
                    if protocol == "TCP":
                        if target_bitrate in object.keys():
                            target_bitrate = object["target_bitrate"]
                        else: 
                            target_bitrate = None
                elif "intervals" == key:
                    for interval in object:
                        bps.append(interval["streams"][0]["bits_per_second"] / BitsUnit)
                        if protocol == "TCP":
                            retransmits.append(interval["streams"][0]["retransmits"])
    else:
        experiment_data = {}
        bps_list = []
        retransmits_list = []
        for i in range(1, iterations + 1):
            logger.debug("Processing iteration {} as file {}...".format(i, log_filename.format(p4code, i, mode)))
            with open(experiment_data_source_path + log_filename.format(p4code, i, mode), "r") as f:
                iperf_log = json.load(f)
                for key, object in iperf_log.items():
                    if "start" == key:
                        if "test_start" not in object.keys():
                            continue
                        protocol = object["test_start"]["protocol"]
                        target_ip = object["connected"][0]["remote_host"]
                        if protocol == "TCP":
                            if "target_bitrate" in object.keys():
                                target_bitrate = object["target_bitrate"]
                            else: 
                                target_bitrate = None
                    elif "intervals" == key:
                        for interval in object:
                            bps.append(interval["streams"][0]["bits_per_second"] / BitsUnit)
                            if protocol == "TCP":
                                retransmits.append(interval["streams"][0]["retransmits"])
                experiment_data.update({i : {"bps": bps, "protocol": protocol, "target_ip": target_ip, "target_bitrate": target_bitrate, "retransmits": retransmits}})
                bps_list.append(pd.Series(experiment_data[i]["bps"]))
                if experiment_data[i]["protocol"] == "TCP":
                    retransmits_list.append(pd.Series(experiment_data[i]["retransmits"]))
            bps.clear()
            retransmits.clear()
        bps_df = pd.DataFrame(bps_list)
        if experiment_data[i]["protocol"] == "TCP":
            retransmits_df = pd.DataFrame(retransmits_list)
            retransmits = retransmits_df.mean()
        bps = bps_df.mean()
        bps_max = bps.max()
        logger.info("Max Bps (Proto: " + protocol + ", Code: " + p4code + "): " + str(bps_max))
    experiment_proto.update({mode : protocol})
    return bps, retransmits, target_ip, protocol, target_bitrate

def plot_iperf_bitrate_in_one_files(p4code, bps_tcp, bps_udp, protocol_t42, protocol_t43, bps_tcp_h = None, bps_udp_h = None, protocol_t42_h = None, protocol_t43_h = None):
    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.set_ylabel("Throughput in MBit/s")
    ax.set_xlabel("Duration in secs")
    bps_tcp = bps_tcp[:len(bps_tcp) - 20]
    bps_udp = bps_udp[:len(bps_udp) - 20]
    
    ax.plot(range(0, len(bps_tcp)), bps_tcp, label="fast-reconfig " + "(" + protocol_t42 + ")", linestyle="dotted")
    ax.plot(range(0, len(bps_udp)), bps_udp, label="fast-reconfig " + "(" + protocol_t43 + ")", linestyle="dotted")
    if bps_tcp_h is not None and bps_udp_h is not None:
        bps_tcp_h = bps_tcp_h[:len(bps_tcp_h) - 20]
        bps_udp_h = bps_udp_h[:len(bps_udp_h) - 20]
        ax.plot(range(0, len(bps_tcp_h)), bps_tcp_h, label="hitless " + "(" + protocol_t42_h + ")", linestyle="dashed")
        ax.plot(range(0, len(bps_udp_h)), bps_udp_h, label="hitless " + "(" + protocol_t43_h + ")", linestyle="dashed")    
    

    # Put a legend below current axis
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=2)
    fig.suptitle("iPerf Bandwidth")
    plt.tight_layout()
    plt.grid(True)
    plt.savefig("IPerf-bps-{}{}.pdf".format(p4code, mode), bbox_inches='tight')
    plt.close()

    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.set_ylabel("Throughput in MBit/s")
    ax.set_xlabel("Duration in secs")
    ax.plot(range(0, len(bps_tcp)), bps_tcp, label="fast-reconfig " + "(" + protocol_t42 + ")", linestyle="dotted")
    if bps_tcp_h is not None:
        ax.plot(range(0, len(bps_tcp_h)), bps_tcp_h, label="hitless " + "(" + protocol_t42_h + ")", linestyle="dashed")

    # Put a legend below current axis
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=2)
    fig.suptitle("iPerf Bandwidth")
    fig.set_tight_layout(True)
    plt.tight_layout()
    plt.grid(True)
    plt.savefig("IPerf-bps-TCP-{}{}.pdf".format(p4code, mode), bbox_inches='tight')
    plt.close()

    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.set_ylabel("Throughput in MBit/s")
    ax.set_xlabel("Duration in secs")
    ax.plot(range(0, len(bps_udp)), bps_udp, label="fast-reconfig " + "(" + protocol_t43 + ")", linestyle="dotted")
    if bps_udp_h is not None:
        ax.plot(range(0, len(bps_udp_h)), bps_udp_h, label="hitless " + "(" + protocol_t43_h + ")", linestyle="dashed")

    # Put a legend below current axis
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=2)
    fig.suptitle("iPerf Bandwidth")
    fig.set_tight_layout(True)

    plt.tight_layout()
    
    plt.grid(True)
    plt.savefig("IPerf-bps-UDP-{}{}.pdf".format(p4code, mode), bbox_inches='tight')
    plt.close()


def plot_iperf_bitrate_in_different_files(p4code, bps_tcp, bps_udp, protocol_t42, protocol_t43):
    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.set_ylabel("Throughput in MBit/s")
    ax.set_xlabel("Duration in secs")
    ax.plot(range(0, len(bps_tcp)), bps_tcp, label="Bandwidth " + "(" + protocol_t42 + ")")

    # Put a legend below current axis
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=1)
    fig.suptitle("IPerf")

    plt.tight_layout()
    
    plt.grid(True)
    plt.savefig("IPerf-{}-bps-{}{}.pdf".format(protocol_t42, p4code, mode), bbox_inches='tight')
    plt.close()
    
    fig = plt.figure()
    ax = fig.add_subplot(211)
    ax.set_ylabel("Throughput in MBit/s")
    ax.set_xlabel("Duration in secs")
    # Put a legend below current axis
    ax.plot(range(0, len(bps_udp)), bps_udp, label="Bandwidth " + "(" + protocol_t43 + ")")
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=1)
    fig.suptitle("IPerf UDP {}")

    plt.tight_layout()
    
    plt.grid(True)
    plt.savefig("IPerf-{}-bps-{}{}.pdf".format(protocol_t43, p4code, mode), bbox_inches='tight')
    plt.close()

def plot_iperf_tcp_retransmits(mode, p4code, retransmits_tcp, retransmits_udp):
    fig, ax = plt.subplots(1,1, figsize=(8,2))
    ax.set_xlabel("Duration in secs")
    ax.set_ylabel("Retransmit Counts")
    ax.plot(range(0, len(retransmits_tcp)), retransmits_tcp, linestyle="dashed", label="Retransmits")
    x_ticks = ax.get_xticks() * MODES[mode]["export_interval"]
    ax.set_xticklabels(x_ticks)
    ax.legend(bbox_to_anchor =(0.5,-0.66), loc='lower center', ncol=1)
    fig.suptitle("IPerf")
    plt.tight_layout()
    plt.savefig("IPerf-TCP-Retransmits-{}{}.pdf".format(p4code, mode), bbox_inches='tight')
    plt.close()

def evaluate_time_measurement(mode, p4code):
    """
    Create a processed CSV file from the collected timemeasurement data.
    """
    df = pd.read_csv(experiment_data_source_path + "time_measurement-{}{}.csv".format(p4code, mode))
    new_df = pd.DataFrame()
    new_df["protocol"] = df["protocol"]
    new_df["iteration"] = df["iteration"]
    new_df["swap_id"] = df["swap_id"]
    new_df["total"] = ((df["swap_end"] - df["swap_started"]) / 1000).round(decimals=3)
    new_df["code_swap"] = ((df["initial_step_start"] - df["swap_started"]) / 1000).round(decimals=3)
    new_df["initialization"] = ((df["initial_step_end"] - df["initial_step_start"]) / 1000).round(decimals=3)
    new_df = new_df.groupby(["protocol", "swap_id"]).mean().reset_index().drop("iteration", axis=1).round(decimals=3)
    new_df.to_csv("evaluated_time_measurement-{}{}.csv".format(p4code, mode), index=False)


def merge_time_measurement(p4code):
    """
    Merge the time measurement data of multiple runs together in one file.
    """
    merge_df = pd.DataFrame()
    dfs = []
    for dim in MODES.keys():
        df : pd.DataFrame = pd.read_csv("evaluated_time_measurement-{}{}.csv".format(p4code, dim))
        df.insert(0, "dev_init_mode", [dim[1:] for i in range(len(df.index))])
        df.insert(0, "p4code", [p4code for i in range(len(df.index))])
        dfs.append(df)
    merge_df = pd.merge(dfs[0], dfs[1], how="outer", on=list(dfs[0].columns))
    merge_df.to_csv("merged_evaluated_time_measurement-{}.csv".format(p4code), index=False)

def create_aggregated_latex_time_measurement_table(p4code):
    """
    Creates an aggregated time measurement table in LaTeX format out of a CSV file.
    """
    df : pd.DataFrame = pd.read_csv("merged_evaluated_time_measurement-{}.csv".format(p4code))
    df = df.drop(["p4code", "swap_id"], axis=1)
    merge_df = df.groupby(["dev_init_mode","protocol"]).mean().reset_index()
    merge_df = merge_df.reindex(columns = [col for col in df.columns if col != 'total'] + ['total'])
    # merge_df.to_csv("test.csv", index=False)
    # merge_df : pd.DataFrame = pd.read_csv("test.csv")
    merge_df.style.set_table_styles([
    {'selector': 'toprule', 'props': ':hline;'},
    {'selector': 'midrule', 'props': ':hline;'},
    # {'selector': 'tr', 'props': ':hline;'},
    {'selector': 'bottomrule', 'props': ':hline;'},
], overwrite=False).to_latex("time_measurement_meaned_swap-{}.tex".format(p4code), convert_css=True, position_float="centering", clines="all;data", column_format="".join(["|c" for i in range(len(df.columns))]) + "|")

def create_latex_time_measurement_table(p4code):
    """
    Creates a time measurement table containing all iterations in LaTeX format out of a CSV file.
    """
    df : pd.DataFrame = pd.read_csv("merged_evaluated_time_measurement-{}.csv".format(p4code))
    df = df.drop("p4code", axis=1)
    df = df.reindex(columns = [col for col in df.columns if col != 'total'] + ['total'])
    df.style.hide(axis="index").set_table_styles([
    {'selector': 'toprule', 'props': ':hline;'},
    {'selector': 'midrule', 'props': ':hline;'},
    # {'selector': 'tr', 'props': ':hline;'},
    {'selector': 'bottomrule', 'props': ':hline;'},
], overwrite=False).to_latex("time_measurement-{}.tex".format(p4code), convert_css=True, position_float="centering", clines="all;data", column_format="".join(["|c" for i in range(len(df.columns))]) + "|")


for p4code in P4CODE:

    for mode, metadata in MODES.items():
        bps_tcp, retransmits_tcp, target_ip_t42, protocol_t42, target_bitrate_t42 = create_connection_line("iperf-c-{}-{}{}.json", mode, p4code, metadata["iterations"])
        bps_udp, retransmits_udp, target_ip_t43, protocol_t43, target_bitrate_t43 = create_connection_line("iperf-c-{}-UDP-{}{}.json", mode, p4code, metadata["iterations"])
        plot_iperf_bitrate_in_different_files(mode, p4code, bps_tcp, bps_udp, protocol_t42, protocol_t43)
        plot_iperf_bitrate_in_one_files(mode, p4code, bps_tcp, bps_udp, protocol_t42, protocol_t43)
        if experiment_proto[mode] == "TCP":
            plot_iperf_tcp_retransmits(mode, p4code, retransmits_tcp, retransmits_udp)
        evaluate_time_measurement(mode, p4code)
    
    merge_time_measurement(p4code)
    create_latex_time_measurement_table(p4code)
    create_aggregated_latex_time_measurement_table(p4code)


for p4code in P4CODE:
    bps_tcp, retransmits_tcp, target_ip_t42, protocol_t42, target_bitrate_t42 = create_connection_line("iperf-c-{}-{}{}.json", "-fast-reconfig", p4code, MODES["-fast-reconfig"]["iterations"])
    bps_udp, retransmits_udp, target_ip_t42_udp, protocol_t42_udp, target_bitrate_t43 = create_connection_line("iperf-c-{}-UDP-{}{}.json", "-fast-reconfig", p4code, MODES["-fast-reconfig"]["iterations"])
    bps_tcp_h, retransmits_tcp_h, target_ip_t42_h, protocol_t42_h, target_bitrate_t42_h = create_connection_line("iperf-c-{}-{}{}.json", "-hitless", p4code, MODES["-hitless"]["iterations"])
    bps_udp_h, retransmits_udp_h, target_ip_t42_udp_h, protocol_t42_udp_h, target_bitrate_t43_h = create_connection_line("iperf-c-{}-UDP-{}{}.json", "-hitless", p4code, MODES["-hitless"]["iterations"])

    plot_iperf_bitrate_in_one_files("", p4code, bps_tcp, bps_udp, protocol_t42, protocol_t42_udp, bps_tcp_h, bps_udp_h, protocol_t42_h, protocol_t42_udp_h)