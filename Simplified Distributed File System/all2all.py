import socket
import random
import time

import os
import os.path

from enum import Enum

from membership_list import MembershipList, Status
from metadata_list import MetadataList, FileStatus
from messages import create_message, MessageType
from protocol import ProtocolBase, ProtocolType

from utils import list_to_str, id_to_address, demo_print, debug_print

class ResponseStatus(Enum):
    OKAY = "okay"
    CONFLICT = "write-read or write-write conflict"
    FILE_NOT_FOUND = "file not found"

class All2All(ProtocolBase):
    @staticmethod
    def get_type():
        return ProtocolType.ALL2ALL

    @staticmethod
    def process_message(address, message_json, mem_list, meta_list, self_id, writing_local_fname, writing_sdfs_fname, reading_local_fname, reading_sdfs_fname):
        message_type = message_json["type"]

        if message_type == MessageType.HEARTBEAT.value:
            sender_id = message_json["sender_id"]
            seqnum = message_json["seqnum"]
            sender_host = message_json["sender_host"]
            sender_port = message_json["sender_port"]

            debug_print("recieved heartbeat from {}".format(sender_id))

            if mem_list.contains_node(sender_id):
                # check that the node is alive so we do not revive a failed node
                if mem_list.is_alive(sender_id):
                    mem_list.update_state(sender_id, Status.ALIVE, seqnum, time.time())
            else:
                mem_list.add_node(sender_id, sender_host, sender_port)

        elif message_type == MessageType.REPORT.value:
            sender_id = message_json["sender_id"]
            file_list = message_json["file_list"]
            debug_print(f"recieved file list at {sender_id}: {file_list}")
            with mem_list.lock:
                debug_print(f'{sender_id in mem_list.nodes.keys()}, {mem_list.nodes[sender_id].status == Status.ALIVE}')
                condition = sender_id in mem_list.nodes.keys() and mem_list.nodes[sender_id].status == Status.ALIVE
            if condition:
                with meta_list.lock:
                    meta_list.update_node_file_list(sender_id, file_list)
            debug_print(meta_list)

        elif message_type == MessageType.LEAVE.value:
            sender_id = message_json["sender_id"]
            mem_list.mark_left(sender_id)

        # Master get put request from client
        elif message_type == MessageType.PUT.value:
            debug_print('Receives PUT from', address)
            sender_id = message_json["sender_id"]
            sender_host = message_json["sender_host"]
            sender_port = message_json["sender_port"]
            sdfs_fname = message_json["sdfs_fname"]

            # with mem_list.lock and meta_list.lock:
            target_hosts, target_ports, response_status = All2All.calc_put_response(sdfs_fname, sender_id, mem_list, meta_list)
            debug_print(target_hosts, target_ports, response_status.value)
                # reply to PUT initiator with list of addr for storing the replicas
            All2All.send_put_response(sender_host, sender_port, target_hosts, target_ports, response_status)
            
            debug_print('Sent PUT_RES to', address)

        # Client get put response from master
        elif message_type == MessageType.PUT_RES.value:
            debug_print('Receives PUT_RES from', address)
            target_hosts = message_json["target_hosts"].split(' ')
            target_ports = message_json["target_ports"].split(' ')
            response_status = message_json["response_status"]

            if response_status == ResponseStatus.CONFLICT:
                debug_print("PUT command failed: Write-read or write-write conflict. Wait and try again. (see @908)")
                return
            if response_status == ResponseStatus.FILE_NOT_FOUND:
                debug_print("GET command failed: File does not exist.")
                return

            if not target_hosts[0]:
                debug_print("No one wants the file.")
                return
            else:
                debug_print(f'{target_hosts} wants file')

            All2All.transfer_file(target_hosts, target_ports, writing_local_fname, writing_sdfs_fname)
            All2All.send_put_success(address, self_id, writing_sdfs_fname)

            debug_print('Sent PUT_SUCCESS to', address)

        # Master get put success from client
        elif message_type == MessageType.PUT_SUCCESS.value:
            debug_print('Receives PUT_SUCCESS from', address)
            sender_id = message_json["sender_id"]
            sdfs_fname = message_json["sdfs_fname"]
            with meta_list.lock:
                meta_list.files[sdfs_fname].status = FileStatus.IDLE
                if sender_id in meta_list.files[sdfs_fname].writers:
                    meta_list.files[sdfs_fname].writers.remove(sender_id)

        elif message_type == MessageType.GET.value:
            debug_print('Receives GET from', address)
            sender_id = message_json["sender_id"]
            sender_host = message_json["sender_host"]
            sender_port = message_json["sender_port"]
            sdfs_fname = message_json["sdfs_fname"]

            debug_print(meta_list.files)
            target_hosts, target_ports, response_status = All2All.calc_get_response(sdfs_fname, sender_id, mem_list, meta_list)
            debug_print(target_hosts, target_ports, response_status.value)
            # reply to PUT initiator with list of addr for storing the replicas
            All2All.send_get_response(sender_host, sender_port, target_hosts, target_ports, response_status)
            
            debug_print('Sent GET_RES to', address)

        # Client get put response from master
        elif message_type == MessageType.GET_RES.value:
            debug_print('Receives GET_RES from', address)
            target_hosts = message_json["target_hosts"].split(' ')
            target_ports = message_json["target_ports"].split(' ')
            response_status = message_json["response_status"]

            if response_status == ResponseStatus.CONFLICT:
                debug_print("GET command failed: Write-read conflict. Wait and try again. (see @908)")
                return
            if response_status == ResponseStatus.FILE_NOT_FOUND:
                debug_print("GET command failed: File does not exist.")
                return

            if not target_hosts[0]:
                debug_print("No one has the file or file not availble.")
                return
            else:
                debug_print(f'{target_hosts} has file')

            All2All.request_file(target_hosts, target_ports, reading_local_fname, reading_sdfs_fname)
            All2All.send_get_success(address, self_id, writing_sdfs_fname)

            debug_print('Sent REQ to', address)

        elif message_type == MessageType.GET_SUCCESS.value:
            debug_print('Receives GET_SUCCESS from', address)
            sender_id = message_json["sender_id"]
            sdfs_fname = message_json["sdfs_fname"]
            with meta_list.lock:
                meta_list.files[sdfs_fname].status = FileStatus.IDLE
                if sender_id in meta_list.files[sdfs_fname].readers:
                    meta_list.files[sdfs_fname].readers.remove(sender_id)

        elif message_type == MessageType.REPLICATE.value:
            sdfs_fname = message_json["sdfs_fname"]
            target_ports = message_json["target_ports"]
            target_hosts = message_json["target_hosts"]

            if not target_hosts[0]:
                debug_print("No one wants the file.")
                return
            
            debug_print(f'{target_hosts} wants file')
            All2All.request_file(target_hosts, target_ports, f'sdfs/{sdfs_fname}', sdfs_fname, ignore_self=True)

        elif message_type == MessageType.DELETE.value:
            sdfs_fname = message_json["sdfs_fname"]
            for node_id in meta_list.files[sdfs_fname].ids:
                All2All.send_delete_request(sdfs_fname, node_id)

        elif message_type == MessageType.DELETE_REQ.value:
            sdfs_fname = message_json["sdfs_fname"]
            os.remove(f'sdfs/{sdfs_fname}')

        ## list all VM addresses containing sdfs_fname
        elif message_type == MessageType.LS.value:
            sdfs_fname = message_json["sdfs_fname"]
            sender_id = message_json["sender_id"]
            client_host, client_port = id_to_address(sender_id)
            ls_result = ""
            if sdfs_fname in meta_list.files:
                for node_id in meta_list.files[sdfs_fname].ids:
                    ls_result += f'{node_id}\n'
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                address = (client_host, client_port)
                message = create_message(
                    MessageType.LS_RES,
                    sdfs_fname=sdfs_fname,
                    ls_result=ls_result
                )
                sock.sendto(message, address)

        elif message_type == MessageType.LS_RES.value:
            sdfs_fname = message_json["sdfs_fname"]
            ls_result = message_json["ls_result"]
            demo_print("LS of {}".format(sdfs_fname))
            demo_print(ls_result)

    # Let master know this client want list of nodes with sdfs_fname
    @staticmethod
    def send_get(sdfs_fname, sender_id, sender_host, sender_port, server_host, server_port, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            address = (server_host, server_port)
            message = create_message(
                MessageType.GET,
                sdfs_fname=sdfs_fname,
                sender_id=sender_id,
                sender_port=sender_port,
                sender_host=sender_host,
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, address)

    @staticmethod
    def calc_get_response(sdfs_fname, sender_id, mem_list, meta_list):
        # return list of target hosts and corresponding ports
        target_hosts = []
        target_ports = []

        # get alive nodes in mem_list
        alive_nodes = {}
        with mem_list.lock:
            for id, row in mem_list.nodes.items():
                if row.status == Status.ALIVE:
                    alive_nodes[id] = row.to_dict()

        # mark the file as reading
        with meta_list.lock:
            # if sdfs_fname given matches no file in SDFS
            if sdfs_fname not in meta_list.files.keys():
                return target_hosts, target_ports, ResponseStatus.FILE_NOT_FOUND
            
            if meta_list.files[sdfs_fname].status == FileStatus.WRITING:
                return target_hosts, target_ports, ResponseStatus.CONFLICT

            meta_list.files[sdfs_fname].status = FileStatus.READING
            meta_list.files[sdfs_fname].readers.append(sender_id)

            file_info = meta_list.files[sdfs_fname].to_dict()
            # update alive node
            for id, alive_node in alive_nodes.items():
                if id in file_info["ids"]:
                    target_hosts.append(alive_node["host"])
                    target_ports.append(alive_node["port"])
    
        return target_hosts, target_ports, ResponseStatus.OKAY

    # Master replies
    @staticmethod
    def send_get_response(sender_host, sender_port, target_hosts, target_ports, response_status, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            address = (sender_host, sender_port)
            message = create_message(
                MessageType.GET_RES,
                target_hosts=list_to_str(target_hosts),
                target_ports=list_to_str(target_ports),
                response_status=response_status.value
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, address)

    @staticmethod
    def send_get_success(address, sender_id, sdfs_fname, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.GET_SUCCESS,
                sdfs_fname=sdfs_fname,
                sender_id=sender_id
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, address)

    # get a file from another place, whether a client receives a GET_RES or REPLICATE
    @staticmethod
    def request_file(target_hosts, target_ports, local_fname, sdfs_fname, ignore_self=False, fail_rate=0.0):
        # raise Exception("request_file not implemented")
        start_time = time.time()
        flag = False
        for i in range(len(target_hosts)):
            if not flag:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    host = target_hosts[i]
                    if host == socket.gethostname() and ignore_self:
                        flag = 1
                        continue

                    port = int(target_ports[i]) + 11
                    debug_print('Trying to connect to', (host, port))
                    try:
                        sock.connect((host, port))
                    except:
                        sock.close()
                        continue
                    sock.send(f'{sdfs_fname}'.encode())
                    bytes_expected = int(sock.recv(1024).decode())

                    # sending file over TCP with socket.sendall()
                    with open(local_fname, 'wb') as f:
                        # send file information
                        debug_print(f'Receiving {sdfs_fname} of size {bytes_expected}')
                        bytes_received = 0
                        while bytes_received < bytes_expected:
                            data = sock.recv(1024)
                            f.write(data)
                            bytes_received += len(data)
                            debug_print(f'Receiving {sdfs_fname} of size {bytes_expected} {bytes_received} / {bytes_expected} B')

                    sock.close()
                    flag = True
        end_time = time.time()
        demo_print(f'get time for {local_fname}: {end_time - start_time}')

    # Let master know this client want list of nodes with sdfs_fname, or places to store replicas
    @staticmethod
    def send_put(sdfs_fname, sender_id, sender_host, sender_port, server_host, server_port, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            address = (server_host, server_port)
            message = create_message(
                MessageType.PUT,
                sdfs_fname=sdfs_fname,
                sender_id=sender_id,
                sender_port=sender_port,
                sender_host=sender_host,
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, address)

    # Master calculates a list of nodes
    @staticmethod
    def calc_put_response(sdfs_fname, sender_id, mem_list, meta_list):
        # return list of target hosts and corresponding ports
        target_hosts = []
        target_ports = []

        # get alive nodes in mem_list
        alive_nodes = {}
        with mem_list.lock:
            for id, row in mem_list.nodes.items():
                if row.status == Status.ALIVE:
                    alive_nodes[id] = row.to_dict()

        with meta_list.lock:
            # if sdfs_fname given matches any file in SDFS
            if sdfs_fname in meta_list.files.keys():
                if meta_list.files[sdfs_fname].status == FileStatus.IDLE:
                    # mark the file as writing
                    meta_list.files[sdfs_fname].status = FileStatus.WRITING
                    meta_list.files[sdfs_fname].writers.append(sender_id)
                    file_info = meta_list.files[sdfs_fname].to_dict()
                    # update alive node with file
                    for id, alive_node in alive_nodes.items():
                        if id in file_info["ids"]:
                            target_hosts.append(alive_node["host"])
                            target_ports.append(alive_node["port"])
                else:
                    return target_hosts, target_ports, ResponseStatus.CONFLICT
            # new file
            else:
                # select 4 machines randomly
                alive_nodes = random.sample(alive_nodes.items(), min(4, len(alive_nodes)))
                for id, alive_node in alive_nodes:
                    target_hosts.append(alive_node["host"])
                    target_ports.append(alive_node["port"])
                
        return target_hosts, target_ports, ResponseStatus.OKAY

    # reply to PUT initiator with list of addr for storing the replicas
    @staticmethod
    def send_put_response(sender_host, sender_port, target_hosts, target_ports, response_status, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.PUT_RES,
                target_hosts=list_to_str(target_hosts),
                target_ports=list_to_str(target_ports),
                response_status=response_status.value
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, (sender_host, sender_port))

    # send local file to local/remote sdfs folder
    @staticmethod
    def transfer_file(target_hosts, target_ports, writing_local_fname, writing_sdfs_fname):
        start_time = time.time()
        for i in range(len(target_hosts)):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                host = target_hosts[i]
                # if host == socket.gethostname():
                #     continue

                port = int(target_ports[i]) + 10
                debug_print('Trying to connect to', (host, port))
                sock.connect((host, port))

                # sending file over TCP with socket.sendall()
                with open(writing_local_fname, 'rb') as f:
                    # send file information
                    debug_print(f'Sending {writing_sdfs_fname} of size {os.path.getsize(writing_local_fname)}')
                    data = writing_sdfs_fname + ' ' + str(os.path.getsize(writing_local_fname))
                    sock.send(data.encode())
                    time.sleep(0.01)
                    while True:
                        bytes_read = f.read(1024)
                        if not bytes_read:
                            # file transmitting is done
                            break
                        sock.sendall(bytes_read)

                sock.close()
        end_time = time.time()
        demo_print(f'put time for size {os.path.getsize(writing_local_fname)}: {end_time - start_time}')

    # reply to master after successfully transferring file
    @staticmethod
    def send_put_success(address, sender_id, sdfs_fname, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.PUT_SUCCESS,
                sdfs_fname=sdfs_fname,
                sender_id=sender_id
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, address)

    # reply to master after successfully transferring file
    @staticmethod
    def send_replicate(sdfs_fname, host, port, target_ids, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            target_hosts = [id_to_address(id)[0] for id in target_ids]
            target_ports = [id_to_address(id)[1] for id in target_ids]
            message = create_message(
                MessageType.REPLICATE,
                sdfs_fname=sdfs_fname,
                target_hosts=target_hosts,
                target_ports=target_ports
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, (host, port))

    # send_message() is ONLY for HEARTBEAT
    @staticmethod
    def send_message(sender_id, mem_list, sock, sender_host, sender_port, seqnum, fail_rate=0.0):
        # debug_print("sending heartbeat")
        for node_id, row in mem_list:
            # only send a heartbeat to other, alive nodes
            if node_id == sender_id or not mem_list.is_alive(node_id):
                continue

            server_addr = (row.host, row.port)
            message = create_message(
                MessageType.HEARTBEAT,
                sender_id=sender_id,
                seqnum=seqnum,
                sender_host=sender_host,
                sender_port=sender_port,
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, server_addr)

    # send my list of files to the master node
    @staticmethod
    def send_report(sender_id, sender_host, sender_port, master_id, master_host, master_port, sock, report_num):
        # NOTE darci: master needs to check its own list at some point and
        # we need to make sure we actually delete files or we could keep track 
        # of files not with the sdfs directory, but with a list in-memory
        if sender_id == master_id:
            return

        file_list = [f for f in os.listdir('sdfs') if os.path.isfile(os.path.join('sdfs', f))]
        
        server_addr = (master_host, master_port)
        message = create_message(
            MessageType.REPORT,
            sender_id=sender_id,
            report_num=report_num,
            sender_host=sender_host,
            sender_port=sender_port,
            file_list=file_list,
        )

        sock.sendto(message, server_addr)

    @staticmethod
    def send_message_interval(failure_detection_time, dissemination_time) -> float:
        # Send to all other nodes within half of dissemination_time
        return dissemination_time / 2

    @staticmethod
    def leave_group(sender_id, mem_list):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(MessageType.LEAVE, sender_id=sender_id)
            for node_id, row in mem_list:
                # only send a leave message to other, alive nodes
                if node_id == sender_id or not mem_list.is_alive(node_id):
                    continue

                server_addr = (row.host, row.port)
                sock.sendto(message, server_addr)

            # clear the membership list. allows rejoining without restarting the program.
            mem_list.clear()

    @staticmethod
    def timeout_interval(failure_detection_time, dissemination_time) -> float:
        return failure_detection_time

    @staticmethod
    def send_delete(sdfs_fname, master_host, master_port, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.DELETE,
                sdfs_fname=sdfs_fname
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, (master_host, master_port))

    @staticmethod
    def send_delete_request(sdfs_fname, node_id, fail_rate=0.0):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.DELETE_REQ,
                sdfs_fname=sdfs_fname
            )

            # send message unless dropped, according to fail_rate
            if random.random() >= fail_rate:
                sock.sendto(message, id_to_address(node_id))

    @staticmethod
    def send_ls_request(sdfs_fname, sender_id, master_host, master_port):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = create_message(
                MessageType.LS,
                sdfs_fname=sdfs_fname,
                sender_id=sender_id
            )

            sock.sendto(message, (master_host, master_port))
    