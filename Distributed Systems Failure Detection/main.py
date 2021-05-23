import time
import socket
from enum import Enum
import json
import pickle
from collections import namedtuple
import threading

T_FAIL = T_CLEANUP = 1

T_HEARTBEAT = 1
T_GOSSIP = 1

GOSSIP_B = 4

    def join_group(self):
        # send UDP to introducer
        # recieve membership list from introducer (and what mode we are in?)
        # initialize my membership list
        # start doing node-like things (sending heartbeats, checking for failures)
        pass

    # TODO: don't want this. only check for failures when updating rest of list??
    # TODO: I think we check for failures every k seconds?
    def check_for_failures(self):
        new_membership_list = self.membership_list
        for node_id, status in self.membership_list.items():
            heartbeat_counter, last_updated, health = status
            # mark as failed if T_FAIL seconds since heartbeat recieved
            if health == NodeHealth.ALIVE and time.time() > last_updated + T_FAIL:
                new_membership_list[node_id] = (heartbeat_counter, time.time(), NodeHealth.FAILED)
            # remove from list if T_CLEANUP seconds since marked as failed
            elif health == NodeHealth.FAILED and time.time() > last_updated + T_CLEANUP:
                new_membership_list.pop(node_id)

    # def broadcast(self):
    #     if self.mode == HeartbeatMode.GOSSIP:
    #         self.gossip()
    #     elif self.mode == HeartbeatMode.ALL_TO_ALL:
    #         self.send_to_all()

    # in all-to-all we listen from heartbeats from all



### ALL-TO-ALL

# periodically send heartbeats to everyone in your list
# periodically check for messages (heartbeats, mode change, leaving)
# periodically check for failure timeouts/failures

# NODES
# contact introducer (get mode, membership list, join introducer's membership list)


### ALL-TO-ALL




### ALL-TO-ALL
### on startup:
# contact introducer. get list of alive members & check that in all-to-all mode
# start up threads for sending heartbeats, checking for failures, listening for heartbeats, and listening for commands

### commands:
#   LEAVE: send leaving message to... normal people?
#   GOSSIP: switch to gossip mode (need to track heartbeats & recieved time)
#   ALL-TO-ALL: switch to all-to-all mode (basically just heartbeats send to all instead of membership lists to some?)
#   LIST: log membership list
#   JOIN: contact introducer. get alive machines

### contact introducer
# send message to request join
# get message with membership list & mode

### send heartbeats
# send heartbeats to everyone in your membership list

### check for failures
# if no heartbeat recieved in T_FAIL seconds, 
# after T_CLEANUP seconds, remove from list? or just mark as deleted

### listen for heartbeats
# if leave message, remove from list? or just mark as left


# Go ahead and use broadcast to change modes or broadcast leave
# Introducer can ask for a node to leave if it timesout? (false positive)

INTRODUCER_HOST = 'fa20-cs425-g22-01.cs.illinois.edu'
FROM_INTRODUCER = 1703
TO_INRODUCER = 1170

NodeId = namedtuple('NodeId', 'hostname port init_time')

class NodeStatus(Enum):
    ALIVE = 0
    FAILED = 1
    LEFT = 2
    DELETED = 3

class HeartbeatMode(Enum):
    GOSSIP = 0
    ALL-TO-ALL = 1

class Node:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.membership_list = {}
        self.mode = HeartbeatMode.GOSSIP

        # introducer: always listen for new joins
        if self.hostname == INTRODUCER_HOST:
            t = threading.Thread(target = self.listen_for_joins)
            t.start()
        # normal node: connect to the introducer otherwise
        else:
            self.join_group()
        # all nodes: always listen for heartbeats
        t = threading.Thread(target = self.listen_for_heartbeats)
        t.start()

        # gossip: periodically send gossip
        if self.mode == HeartbeatMode.GOSSIP:
            t = threading.Thread(target = self.send_gossip)
        # all-to-all: periodicaly send heartbeats
        else:
            t = threading.Thread(target = self.send_heartbeat)

    def join_group(self):
        # tell introducer you want to join the group
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', TO_INTRODUCER))
        sock.sendto(b'JOIN', (INTRODUCER_HOST, FROM_INTRODUCER))

        # get mode and membership list from introducer
        message, addr = sock.recvfrom(65535)
        command, message = message.split(" ", 1)
        if command == "JOINED":
            # set heartbeat mode
            heartbeat_mode, message = message.split(" ", 1)
            self.heartbeat_mode = pickle.loads(heartbeat_mode)
            # set membership list with ALIVE nodes
            recv_membership_list = pickle.loads(message)
            for node_id, record in recv_membership_list:
                (heartbeat_count, last_updated, status) = record
                if status == NodeStatus.ALIVE:
                    self.membership_list[node_id] = (heartbeat_count, time.time(), status)
                    self.mode = HeartbeatMode.GOSSIP

    def listen_for_joins(self):
        self.introducer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.introducer_sock.bind((self.introducer_sock.gethostname(), FROM_INTRODUCER))
        self.introducer_sock.listen(5)
        while True:
            client, addr = self.introducer_sock.accept()
            t = threading.Thread(target = self.accept_join, args = client

class HeartbeatMode(Enum):
    GOSSIP = 0
    ALL_TO_ALL = 1