import sys
import os
import socket
import time
import json
import random
import logging

from enum import IntEnum
from threading import RLock, Thread
from _thread import interrupt_main

p1 = 3490 # Listener
p2 = 3491 # Talker

T_HEARTBEAT = 0.5
T_FAIL = 4
T_CLEANUP = 6
GOSSIP_B = 4
MESSAGE_DROP_RATE = 0

class NodeStatus(IntEnum):
    OFFLINE = 0
    ONLINE = 1
    FAILED = 2
    LEFT = 3

class Mode(IntEnum):
    ALL = 0
    GOSSIP = 1

class Node:
    def __init__(self, role, mode):
        logging.basicConfig(filename=socket.gethostname().split('.')[0].split('-')[-1]+'.log')
        # logging.basicConfig()
        logging.root.setLevel(logging.NOTSET)

        self.introducer_host = 'fa20-cs425-g22-01.cs.illinois.edu'

        self.hostname = socket.gethostname()
        self.addr = socket.gethostbyname(self.hostname)
        self.s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s1.bind((self.hostname, p1))
        self.s2.bind((self.hostname, p2))

        self.init_time = str(round(time.time(), 2))
        self.node_id = self.hostname + " @ " + self.init_time

        self.mode = mode

        self.heartbeat_counter = 0

        self.member_list = {}
        self.member_lock = RLock()
        self.mode_lock = RLock()

        self.joined = False
        self.role = role

    def merge_member(self, m2):
        # Merge received member list with local member list
        self.member_lock.acquire()
        for node_id, recv_value in m2.items():
            recv_node_status, recv_heartbeat_counter, _ = recv_value
            # leave the group if nodes mislabeled you as failed
            if node_id == self.node_id:
                if recv_node_status != NodeStatus.ONLINE:
                    self.log_visible("Failed: supposedly failed (false positive)... exiting")
                    interrupt_main()
            # update the membership list for all other recieved nodes
            else:
                # update existing record if recieved newer heartbeat for an online node
                if node_id in self.member_list:
                    curr_node_status, curr_heartbeat_counter, _ = self.member_list[node_id]
                    if curr_node_status == NodeStatus.ONLINE and recv_heartbeat_counter > curr_heartbeat_counter and recv_node_status == NodeStatus.ONLINE:
                        self.member_list[node_id] = (recv_node_status, recv_heartbeat_counter, time.time())
                    elif curr_node_status == NodeStatus.ONLINE and recv_node_status == NodeStatus.FAILED:
                        self.log_visible("Failed: {} supposedly failed".format(node_id))
                        self.member_list[node_id] = (recv_node_status, recv_heartbeat_counter, time.time())
                # insert new record if we see a new online node (join)
                elif node_id not in self.member_list:
                    if recv_node_status == NodeStatus.ONLINE:
                        self.member_list[node_id] = (recv_node_status, recv_heartbeat_counter, time.time())
                        self.log_visible("Joined: {} supposedly joined the group".format(node_id))

        self.member_lock.release()

    def listener(self):
        while not self.joined:
            time.sleep(0.1)
            pass

        while True:
            msg, addr = self.s1.recvfrom(1024)
            msg = msg.decode()
            # logging.debug(msg)

            msg = json.loads(msg)

            if msg["type"] == "join":
                node_id = msg["node_id"]
                self.log_visible("Joined: {} joined the group".format(node_id))
                self.member_lock.acquire()
                recv_node_status, recv_heartbeat_counter, _ = msg["timestamp"]
                self.member_list[node_id] = (recv_node_status, recv_heartbeat_counter, time.time())
                data = {"type": "join_success", "mode": int(self.mode), "member_list": self.member_list}
                data = json.dumps(data)
                sent_byte = self.s2.sendto(data.encode(), (addr[0], p1)) # addr == (addr[0], p2)

                self.member_lock.release()

            elif msg["type"] == "heartbeat":
                logging.debug("Received heartbeat from " + str(addr[0]))
                m2 = msg["member_list"]
                self.merge_member(m2)

            elif msg["type"] == "leave":
                node_id = msg["node_id"]
                self.log_visible("Left: {} left the group".format(node_id))
                self.member_lock.acquire()
                if node_id in self.member_list and self.member_list[node_id][0] == NodeStatus.ONLINE:
                    _, heartbeat_counter, _ = self.member_list[node_id]
                    self.member_list[node_id] = (NodeStatus.LEFT, heartbeat_counter, time.time())
                self.member_lock.release()

            elif msg["type"] == "switch":
                new_mode = Mode(msg["mode"])
                self.mode_lock.acquire()
                self.mode = new_mode
                self.mode_lock.release()
                self.log_visible("Switched: switched to heartbeat mode " + self.mode2str(new_mode))

    def heartbeater(self):
        while not self.joined:
            time.sleep(0.1)
            pass

        while True:
            t0 = time.time()
            sent_byte = 0

            self.member_lock.acquire()
            # Check for failures before heartbeating
            nodes_to_delete = []
            for node_id, value in self.member_list.items():
                if node_id == self.node_id:
                    continue

                node_status, curr_heartbeat_counter, last_updated = value
                # mark node as failed if node is currently online and hasn't updated heartbeat for a while
                if node_status == NodeStatus.ONLINE and time.time() - last_updated > T_FAIL:
                    self.member_list[node_id] = (NodeStatus.FAILED, curr_heartbeat_counter, time.time())
                    self.log_visible("Failed: {} didn't heartbeat".format(node_id))
                # delete node from member_list if node has failed and passed cleanup time
                elif (node_status == NodeStatus.FAILED or node_status == NodeStatus.LEFT) and time.time() - last_updated > T_CLEANUP:
                    self.log_visible("Delete: {} stopped cleanup seconds ago".format(node_id))
                    nodes_to_delete.append(node_id)

            for node_id in nodes_to_delete:
                self.member_list.pop(node_id, None)
            self.member_lock.release()

            self.mode_lock.acquire()
            mode = self.mode
            self.mode_lock.release()

            self.member_lock.acquire()
            if mode == Mode.GOSSIP:
                alive_members = {}
                for node_id, (node_status, heartbeat_counter, last_updated) in self.member_list.items():
                    if node_status == NodeStatus.ONLINE and node_id != self.node_id:
                        alive_members[node_id] = (node_status, heartbeat_counter, last_updated)

                if not alive_members:
                    self.member_lock.release()
                    time.sleep(0.1)
                    continue
                
                recipients = random.sample(list(alive_members.items()), k = min(GOSSIP_B, len(list(alive_members.items()))))

                for node_id, (node_status, heartbeat_counter, last_updated) in recipients:
                    self.heartbeat_counter += 1
                    self.member_list[self.hostname+" @ "+self.init_time] = [NodeStatus.ONLINE, self.heartbeat_counter, time.time()]

                    if (random.random() > MESSAGE_DROP_RATE):
                        hostname, _ = node_id.split(" @ ")

                        data = {"type": "heartbeat", "member_list": self.member_list}
                        data = json.dumps(data)

                        # logging.debug(data)

                        addr = socket.gethostbyname(hostname)
                        sent_byte += self.s2.sendto(data.encode(), (addr, p1))
                        logging.info('Sent ' + str(sent_byte) + ' bytes to ' + node_id)

            elif mode == Mode.ALL:
                data = {"type": "heartbeat", "member_list": {self.node_id: self.member_list[self.node_id]}}
                data = json.dumps(data)

                # logging.debug(data)

                for node_id, (node_status, heartbeat_counter, last_updated) in self.member_list.items():
                    if node_id == self.node_id:
                        continue

                    self.heartbeat_counter += 1
                    self.member_list[self.hostname+" @ "+self.init_time] = [NodeStatus.ONLINE, self.heartbeat_counter, time.time()]

                    if (random.random() > MESSAGE_DROP_RATE):
                        hostname, _ = node_id.split(" @ ")
                        if node_status != NodeStatus.ONLINE:
                            continue

                        addr = socket.gethostbyname(hostname)
                        sent_byte += self.s2.sendto(data.encode(), (addr, p1))

                logging.info('Sent ' + str(sent_byte) + ' bytes to all')


            self.member_lock.release()
            time.sleep(T_HEARTBEAT)

            t1 = time.time()
            bw = sent_byte / (t1 - t0)

    def process_input(self, command):
        command = command.lower()
        logging.debug('User entered: ' + command)

        if (command == 'join' and not self.joined):
            if self.role == 'introducer':
                self.member_lock.acquire()
                self.member_list[self.hostname+" @ "+self.init_time] = [NodeStatus.ONLINE, self.heartbeat_counter, time.time()]
                self.member_lock.release()
                self.log_visible('Joining: joining as introducer')

            elif self.role == 'server':
                # STEP 1: Send join message to introducer
                data = {"type": "join", "node_id": self.node_id, "timestamp": [NodeStatus.ONLINE, self.heartbeat_counter, time.time()]}
                data = json.dumps(data)

                # logging.debug(data)

                sent_byte = self.s2.sendto(data.encode(), (self.introducer_host, p1))

                # STEP 2: Wait for introducer response
                msg, addr = self.s1.recvfrom(1024)
                hostname = socket.gethostbyaddr(addr[0])[0]
                msg = msg.decode()
                # logging.debug(msg)

                msg = json.loads(msg)

                self.member_lock.acquire()
                recv_member_list = msg["member_list"]
                self.member_list = {}
                for node_id, (recv_node_status, recv_heartbeat_counter, _) in recv_member_list.items():
                    if recv_node_status == NodeStatus.ONLINE:
                        self.member_list[node_id] = (recv_node_status, recv_heartbeat_counter, time.time())
                        logging.debug("Joined: {} supposedly joined the group".format(node_id))
                self.member_lock.release()

                self.mode_lock.acquire()
                self.mode = Mode(msg["mode"])
                self.mode_lock.release()

                self.log_visible('Joining: joining the group via introducer (mode = {})'.format(self.mode2str(self.mode)))

            self.joined = True

        elif (command == 'leave'):
            self.member_lock.acquire()

            data = {"type": "leave", "node_id": self.node_id}
            data = json.dumps(data)

            sent_byte = 0

            for node_id, (node_status, heartbeat_counter, last_updated) in self.member_list.items():
                hostname, _ = node_id.split(" @ ")
                if node_status != NodeStatus.ONLINE or node_id == self.node_id:
                    continue

                addr = socket.gethostbyname(hostname)
                sent_byte += self.s2.sendto(data.encode(), (addr, p1))

            logging.debug('Sent ' + str(sent_byte) + ' bytes to all')
            self.log_visible('Leaving: leaving network')

            self.member_lock.release()
            interrupt_main()

        elif (command == 'list'):
            self.log_visible("                         MEMBERSHIP LIST")
            self.log_visible("=================================================================")
            for node_id, value in self.member_list.items():
                hostname, _ = node_id.split(" @ ")
                (node_status, heartbeat_counter, last_updated) = value
                self.log_visible("NODE ID:\t{}\nSTATUS:\t\t{}\nCOUNTER:\t{}\nLAST UPDATE:\t{:.2f}".format(node_id, self.status2str(node_status), heartbeat_counter, last_updated))
                self.log_visible("-----------------------------------------------------------------")
        elif (command == 'switch'):
            new_mode = Mode((int(self.mode) + 1) % 2)
            self.mode = new_mode
            self.log_visible("Switching: switching to " + self.mode2str(new_mode))
            data = {"type": "switch", "mode": new_mode}
            data = json.dumps(data)
            for node_id, value in self.member_list.items():
                if node_id == self.node_id:
                    continue
                hostname, _ = node_id.split(" @ ")
                (node_status, heartbeat_counter, last_updated) = value
                if node_status == NodeStatus.ONLINE:
                    addr = socket.gethostbyname(hostname)
                    self.s2.sendto(data.encode(), (addr, p1))

        elif command == 'id':
            self.log_visible("Node ID: " + self.node_id)
        elif command == 'mode':
            self.log_visible("Mode: " + self.mode2str(self.mode))

    def status2str(self, node_status):
        if node_status == NodeStatus.FAILED:
            status = "FAILED"
        elif node_status == NodeStatus.ONLINE:
            status = "ONLINE"
        elif node_status == NodeStatus.LEFT:
            status = "LEFT"
        else:
            status = "OFFLINE"
        return status

    def mode2str(self, node_status):
        if node_status == Mode.GOSSIP:
            status = "GOSSIP"
        else:
            status = "ALL"
        return status

    def log_visible(self, arg):
        print(arg)
        logging.warning(arg)

    def commander(self):
        while True:
            self.process_input(input())
