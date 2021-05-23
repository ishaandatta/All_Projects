from enum import Enum
import threading
import argparse
import socket
import signal
import time
import sys
import os
import os.path
import logging
import shutil
import random

from all2all import All2All
from utils import get_host_number_id, get_hostname, generate_id, demo_print, debug_print
from protocol import ProtocolBase, ProtocolType
from messages import parse_and_validate_message
from membership_list import MembershipList, Status
from metadata_list import MetadataList
# from file_list import FileList

protocol = None
mem_list = MembershipList()
meta_list = MetadataList()

self_id = None
in_group = False
writing_local_fname = ""
writing_sdfs_fname = ""
reading_local_fname = ""
reading_sdfs_fname = ""
is_master = False

def listen_thread(server_ip, port, is_introducer):
    """
    Listen for messages from group members. Update membership list accordingly.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((server_ip, int(port)))

    while True:
        data, address = sock.recvfrom(4096)
        request_json = parse_and_validate_message(data)
        if request_json is None:
            # The data received is not valid
            continue

        if is_introducer:
            # TODO: change this
            protocol.process_join_request(address, request_json, mem_list, sock)

        if not in_group:
            continue

        protocol.process_message(address, request_json, mem_list, meta_list, self_id, writing_local_fname, writing_sdfs_fname, reading_local_fname, reading_sdfs_fname)

def file_listen_thread(server_ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((server_ip, int(port) + 10))
    sock.listen()

    while True:
        conn, addr = sock.accept()
        debug_print('Got connection from', addr)
        file_metadata = conn.recv(1024).decode().split(' ')
        debug_print('File Metadata:', file_metadata)
        filename = f'sdfs/{file_metadata[0]}'
        bytes_expected = int(file_metadata[1])
        
        debug_print(f'Receiving {filename} of size {bytes_expected}')

        conn.settimeout(5.0)
        with open(filename, "wb") as f:
            _i = 0
            bytes_received = 0
            while bytes_received < bytes_expected:
                bytes_read = conn.recv(1024)
                if not bytes_read:
                    break
                _i += 1
                bytes_received += len(bytes_read)
                # debug_print(f'{filename}: Received packet {_i}, {bytes_received} / {bytes_expected} B')
                f.write(bytes_read)

        debug_print(f"Received {filename}")
        # update file list at current node
        # with file_list.lock:
        #     file_list.files[filename] = filename

        conn.close()

def file_send_thread(server_ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((server_ip, int(port) + 11))
    sock.listen()

    while True:
        conn, addr = sock.accept()
        debug_print('Got connection from', addr)

        # receive an sdfs_fname
        filename = conn.recv(1024).decode()
        debug_print('Filename:', filename)
        filename = f'sdfs/{filename}'
        filesize = os.path.getsize(filename)
        conn.send(filesize.encode())
        time.sleep(0.01)

        with open(filename, "rb") as f:
            bytes_sent = 0
            while bytes_sent < filesize:
                data = f.read(1024)
                sock.sendall(data)
                bytes_sent += len(data)
                debug_print(f'Sending {filename}, {bytes_sent} / {filesize} B')

        conn.close()
        debug_print(f"Sent {filename} to {addr}")

# periodically send heartbeats to other alive nodes & file reports to the master
def send_thread(
    self_host, self_port, failure_detection_time, dissemination_time, failure_rate
):
    """
    Send messages to group members periodically.
    """
    # "static" sequence number for this function
    send_thread.seqnum = 0
    send_thread.report_num = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            if in_group:
                protocol.send_message(
                    self_id,
                    mem_list,
                    sock,
                    self_host,
                    self_port,
                    send_thread.seqnum,
                    failure_rate
                )

                master_id = self_id

                if is_master:
                    with meta_list.lock:
                        file_list = [f for f in os.listdir('sdfs') if os.path.isfile(os.path.join('sdfs', f))]
                        meta_list.update_node_file_list(master_id, file_list)
                else:
                    protocol.send_report(
                        self_id,
                        self_host,
                        self_port,
                        master_id="", # TODO need whole master node id to compare to ours
                        master_host=args.introducer_host,
                        master_port=args.introducer_port,
                        sock=sock,
                        report_num=send_thread.report_num,
                    )
                
            interval = protocol.send_message_interval(
                failure_detection_time, dissemination_time
            )
            time.sleep(interval)
            send_thread.seqnum += 1
            send_thread.report_num += 1


class CommandType(Enum):
    SWITCH = "switch"
    MEMBERSHIP_LIST = "list"
    DISPLAY_SELF_ID = "id"
    JOIN = "join"
    LEAVE = "leave"
    FAIL = "fail"
    PUT = "put"
    GET = "get"
    DELETE = "delete"
    STORE = "store"
    LS = "ls"
    UNKNOWN = "unknown"


def user_interact_thread(args):
    """
    Take user commands and take action accordingly.
    """
    global protocol, in_group, self_id, is_master, writing_local_fname, writing_sdfs_fname, reading_local_fname, reading_sdfs_fname
    id_num = get_host_number_id(get_hostname())
    while True:
        user_input = input(f"[{id_num}-{protocol.get_type().value}] Enter command: ")
        user_input = user_input.split(' ')
        try:
            command = CommandType(user_input[0].lower())
        except ValueError as e:
            all_commands = ", ".join([c.value for c in CommandType])
            logging.warn(f"Invalid command. Please enter one of: {all_commands}")
            continue

        if command == CommandType.MEMBERSHIP_LIST:
            logging.info(mem_list)
        elif command == CommandType.DISPLAY_SELF_ID:
            logging.info(self_id)
        elif command == CommandType.JOIN:
            if in_group:
                logging.warn("Already in group...")
            else:
                # ensure a blank sdfs folder on join
                if os.path.exists("sdfs") and os.path.isdir("sdfs"):
                    shutil.rmtree("sdfs")
                os.mkdir("sdfs")

                self_id = generate_id(args.host, args.port)
                logging.info(
                    f"Joining group at {args.introducer_host}:{args.introducer_port}"
                )
                protocol.join_group(
                    mem_list,
                    self_id,
                    args.introducer_host,
                    args.introducer_port,
                    args.host,
                    args.port,
                )
                in_group = True
        elif command == CommandType.LEAVE:
            if not in_group:
                logging.warn("Not in group, cannot leave...")
            elif args.introducer:
                logging.warn("Introducer cannot leave group :(")
            else:
                logging.info("Leaving group")
                in_group = False
                # clear out the sdfs folder (disabled for debugging purposes)
                # if os.path.exists("sdfs") and os.path.isdir("sdfs"):
                #     shutil.rmtree("sdfs")
                # os.mkdir("sdfs")
                protocol.leave_group(self_id, mem_list)
                self_id = None
        elif command == CommandType.FAIL:
            os.kill(os.getpid(), signal.SIGTERM)
        elif command == CommandType.PUT:
            if not in_group:
                logging.warn("Not in group, cannot put...")
                continue
            writing_local_fname = user_input[1]
            writing_sdfs_fname = user_input[2]
            # TODO: if current client is master, no need to fetch target_nodes
            if is_master:
                target_hosts, target_ports = protocol.calc_put_response(writing_sdfs_fname, self_id, mem_list, meta_list)
                protocol.transfer_file(target_hosts, target_ports, writing_local_fname, writing_sdfs_fname)
            # TODO: else fetch target_nodes from master
            else:
                master_host, master_port = (args.introducer_host, args.introducer_port)
                protocol.send_put(
                    writing_sdfs_fname,
                    self_id,
                    args.host,
                    args.port,
                    master_host,
                    master_port
                )
        elif command == CommandType.GET:
            if not in_group:
                logging.warn("Not in group, cannot get...")
                continue
            reading_sdfs_fname = user_input[1]
            reading_local_fname = user_input[2]
            # Can't GET if current client is performing writing
            # TODO: if current client is master, no need to fetch target_nodes
            if is_master:
                target_hosts, target_ports = protocol.calc_get_response(reading_sdfs_fname, self_id, mem_list, meta_list)
                protocol.request_file(target_hosts, target_ports, reading_sdfs_fname, reading_local_fname)
            # TODO: else fetch target_nodes from master
            else:
                master_host, master_port = (args.introducer_host, args.introducer_port)
                protocol.send_get(
                    reading_sdfs_fname,
                    self_id,
                    args.host,
                    args.port,
                    master_host,
                    master_port
                )
        elif command == CommandType.STORE:
            if not in_group:
                logging.warn("Not in group, cannot store...")
                continue
            file_list = [f for f in os.listdir('sdfs') if os.path.isfile(os.path.join('sdfs', f))]
            demo_print("STORE @ {}".format(self_id))
            for file in file_list:
                demo_print(file)
        elif command == CommandType.DELETE:
            if not in_group:
                logging.warn("Not in group, cannot delete...")
                continue
            master_host, master_port = (args.introducer_host, args.introducer_port)
            protocol.send_delete(
                user_input[1],
                master_host,
                master_port
            )
        elif command == CommandType.LS:
            if not in_group:
                logging.warn("Not in group, cannot ls...")
                continue
            if not is_master:
                master_host, master_port = (args.introducer_host, args.introducer_port)
                protocol.send_ls_request(
                    user_input[1],
                    self_id,
                    master_host,
                    master_port,
                )
            else:
                with meta_list.lock:
                    demo_print("LS of {}".format(user_input[1]))
                    ls_result = ""
                    if user_input[1] in meta_list.files:
                        for node_id in meta_list.files[user_input[1]].ids:
                            ls_result += f'{node_id}\n'
                    demo_print(ls_result)
        else:
            all_commands = ", ".join([c.value for c in CommandType])
            logging.warn(f"Unknown command. Please enter one of: {all_commands}")

def update_peer_status_thread(failure_detection_time, dissemination_time):
    """
    Periodically go through membership list and mark nodes that timed-out as failed.
    """
    while True:
        if not in_group:
            continue

        # update membership_list
        for node_id, row in mem_list:
            if node_id == self_id or not mem_list.is_alive(node_id):
                continue

            last_recv_hb_time = row.timestamp
            delta = time.time() - last_recv_hb_time

            if delta > failure_detection_time:
                mem_list.mark_failed(node_id)

        if is_master:
            alive_nodes = {}
            with mem_list.lock:
                for id, row in mem_list.nodes.items():
                    if row.status == Status.ALIVE:
                        alive_nodes[id] = row.to_dict()

            with meta_list.lock:
                # alive nodes
                # choose (4-N) target nodes from alive nodes
                for filename, row in meta_list.files.items():
                    if time.time() - meta_list.files[filename].last_request < 5 + (meta_list.files[filename].filesize / 5000000):
                        continue

                    curr_num_replicas = len(meta_list.files[filename].ids)
                    # TODO darci only include non replicates
                    target_nodes = random.sample(alive_nodes.items(), min(4 - curr_num_replicas, len(alive_nodes)))

                    for id, row in target_nodes:
                        protocol.send_replicate(
                            filename,
                            row["host"],
                            int(row["port"]),
                            meta_list.files[filename].ids
                        )

        interval = protocol.timeout_interval(failure_detection_time, dissemination_time)
        time.sleep(interval)


def start_daemon_thread(target_func, *args):
    thread = threading.Thread(target=target_func, args=args)
    thread.daemon = True
    thread.start()
    return thread


def parse_args():
    parser = argparse.ArgumentParser(description="Simple implementation of a distributed file system that uses all-to-all heartbeat.")
    parser.add_argument("--host", default=get_hostname(), help="Host name of this node.")
    parser.add_argument("--port", default=3256, help="Port number to host service on.")
    parser.add_argument(
        "--failure-detection-time",
        default=5,
        help="When failure happens, within this time at least one machine detects it.",
    )
    parser.add_argument(
        "--dissemination-time",
        default=6,
        help="When failure/join/leave happens, every node should update their membership list within this time.",
    )

    parser.add_argument("--introducer", default=False, action="store_true", help="Whether this node is an introducer.")
    parser.add_argument("--introducer-host", help="Introducer's host name, required if this node is not an introducer.")
    parser.add_argument("--introducer-port", help="Introducer's port number, required if this node is not an introducer.")
    parser.add_argument("--message-failure-rate", default=0, help="Rate of dropping message before sending. A float between 0 and 1. Simulate network package drops.")

    args = parser.parse_args()
    if args.introducer is False:
        if args.introducer_host is None or args.introducer_port is None:
            parser.error(
                "--introducer-host/port must be set if the node is not an introducer"
            )

    args.port = int(args.port)
    if args.introducer_port is not None:
        args.introducer_port = int(args.introducer_port)

    args.message_failure_rate = float(args.message_failure_rate)

    return args


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=logging.INFO)

    # ensure an existing local folder
    if not os.path.exists('local'):
        os.makedirs('local')
    # start with a blank sdfs folder
    if os.path.exists("sdfs") and os.path.isdir("sdfs"):
        shutil.rmtree("sdfs")
    os.mkdir("sdfs")

    protocol = All2All

    in_group = args.introducer
    if args.introducer:   
        is_master = True
        self_id = generate_id(args.host, args.port)
        mem_list.add_node(self_id, args.host, args.port)

    # start threads
    start_daemon_thread(listen_thread, args.host, args.port, args.introducer)
    start_daemon_thread(file_listen_thread, args.host, args.port)
    start_daemon_thread(
        send_thread,
        args.host,
        args.port,
        args.failure_detection_time,
        args.dissemination_time,
        args.message_failure_rate,
    )
    start_daemon_thread(
        update_peer_status_thread, args.failure_detection_time, args.dissemination_time
    )
    # use main thread to interact with user
    user_interact_thread(args)
