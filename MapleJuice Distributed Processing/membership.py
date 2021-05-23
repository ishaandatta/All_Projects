import time
import copy
import uuid
import json
import socket
import random
import threading

from membership_utils import (
    MembershipList, 
    MembershipListEntry, 
    Status,
    TimePeriod
)

from constants import (
    DEFAULT_PORT_MEMBERSHIP,
    ALL_HOST_NAMES,
    INTRODUCER_HOST_NAMES,
)

from message import MessageType, Message

GOSSIP_RATE = 1
ALL_ADDRESSES = [(host_name, DEFAULT_PORT_MEMBERSHIP) for host_name in ALL_HOST_NAMES]
INTRODUCER_ADDRESSES = [(host_name, DEFAULT_PORT_MEMBERSHIP) for host_name in INTRODUCER_HOST_NAMES]

class MembershipServer:
    def __init__(self, 
                host = socket.gethostname(), 
                port = DEFAULT_PORT_MEMBERSHIP, 
                mode = "gossip"):
        self.id = str(uuid.uuid4())
        self.ip_address = (host, port)

        self.mem_list = MembershipList(self.id, self.ip_address)
        self.is_introducer = self.ip_address in INTRODUCER_ADDRESSES
        
        self.mode = mode
        self.gossip_rate = GOSSIP_RATE if mode == "gossip" else 1
        
        # Automatically join on initialization
        self.join()

    def checker(self):
        '''check failures in its membership list'''
        ml = self.mem_list
        while True:
            time.sleep(TimePeriod.CHECKER_SLEEP / 100)
            with ml.lock:
                mle = ml.list[self.id]
                # Do nothing if not in `NORMAL` status
                if mle.status != Status.NORMAL:
                    continue
                ml.check_and_delete()

    def sender(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        ml = self.mem_list
        while True:
            time.sleep(TimePeriod.SENDER_SLEEP / 100)

            with ml.lock:
                mle = ml.list[self.id]

                # Send its new membership list to introducers if in `PENDING` status
                if mle.status == Status.PENDING:
                    msg = Message(self.ip_address, MessageType.JOIN).prepare()
                    addresses = INTRODUCER_ADDRESSES
                    for address in addresses:
                        sock.sendto(msg.encode('UTF-8'), tuple(address))

                # Send out heartbeat messages if in `NORMAL` status
                elif mle.status == Status.NORMAL:
                    #print("[DEBUG] sender: status normal")
                    mle.increment()
                    addresses, msg = ml.construct_message(self.gossip_rate)
                    if not addresses:
                        addresses = INTRODUCER_ADDRESSES
                    out_msg = Message(msg).prepare()
                    #print("[DEBUG] about to send a message")
                    #print(addresses)
                    #print(out_msg)
                    for address in addresses:
                        try:
                            sock.sendto(out_msg.encode('UTF-8'), tuple(address))
                        except:
                            print(tuple(address))

    def receiver(self):
        ''' upon receiving message from another sender'''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.ip_address)
        ml = self.mem_list
        while True:
            #time.sleep(TimePeriod.RECEIVER_SLEEP / 100)

            with ml.lock:
                mle = ml.list[self.id]
                # Do nothing if not in `NORMAL` or `PENDING` status
                if mle.status not in [Status.NORMAL, Status.PENDING]:
                    continue

            data, from_address = sock.recvfrom(10000)
            msg = json.loads(data.decode('UTF-8'))
            #print("Receive message from", from_address)
            #print(msg)

            with ml.lock:
                if msg['type'] == MessageType.ML:
                    if mle.status == Status.NORMAL:
                        #self.mem_list.print()
                        ml.update(msg['body'])
                        #print("[DEBUG] received a ML message")
                        #print(msg['body'])
                        #print(int(time.time() * 100))
                        #self.mem_list.print()

                elif msg['type'] == MessageType.SWITCH:
                    self.switch_util()
                    ml.logging.info(f'[SWITCH] Received a switch message and successfully switched to {self.mode}')
                    #print(f"[DEBUG] received a SWITCH message, now in {self.mode} style")

                elif msg['type'] == MessageType.ACK:
                    if mle.status == Status.PENDING:
                        mle.status = Status.NORMAL
                        ml.logging.info(f'[SET] Set {mle.address} status to normal.')
                        #print(f"[DEBUG] moved from PENDING to NORMAL!")

                elif msg['type'] == MessageType.JOIN:
                    if self.is_introducer:
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock2:
                            from_address = msg['body']
                            out_msg = Message("", MessageType.ACK).prepare()
                            sock2.sendto(out_msg.encode('UTF-8'), tuple(from_address))
                            ml.logging.info(f'[ACK] Send ACK message to {from_address}')
                            #print(f"[DEBUG] send ACK message to {from_address}")
                else:
                    print('[ERROR] Invalid message type received')


    def switch(self):
        ''' Switch from gossip-style to all2all-style, and vice versa '''
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            msg = Message("", MessageType.SWITCH).prepare()
            addresses = ALL_ADDRESSES
            for address in addresses:
                s.sendto(msg.encode('UTF-8'), tuple(address))
            print('[INFO] Successfully switched to %s and broadcasted the switch command' % self.mode)

    def switch_util(self):
        if self.mode == "gossip":
            self.mode = "all_to_all"
            self.gossip_rate = 1
        elif self.mode == "all_to_all":
            self.mode = "gossip"
            self.gossip_rate = GOSSIP_RATE
        else:
            print('[ERROR] Invalid current mode %s. Only gossip and all_to_all expected' % self.mode)

    def join(self):
        # Initialize a new id and a new membership list 
        # print('[DEBUG] join() started')
        ml = self.mem_list
        with ml.lock:
            # print('[DEBUG] join() grabbed the lock!')
            self.id = str(uuid.uuid4())
            ml.id  = self.id
            ml.list = {self.id: MembershipListEntry(self.ip_address)}
        
            mle = ml.list[self.id]
            if self.is_introducer:
                mle.status = Status.NORMAL
            else:
                mle.status = Status.PENDING
        # print('[DEBUG] join() finished')

    def leave(self):
        # print('[DEBUG] leave() started')
        ml = self.mem_list
        with ml.lock:
            #print('[DEBUG] leave() grabbed the lock!')
            mle = ml.list[self.id]
            if mle.status in [Status.NORMAL, Status.PENDING]:
                mle.status = Status.LEFT
            else:
                print(f'[ERROR] Process {self.id} cannot leave because its status is {mle.status}')

        # Broadcast its leaving status to selected nodes or introducers
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            addresses, msg = ml.construct_message(self.gossip_rate)
            out_msg = Message(msg).prepare()
            if not addresses:
                addresses = INTRODUCER_ADDRESSES
            for address in addresses:
                s.sendto(out_msg.encode('UTF-8'), tuple(address))
        #print('[DEBUG] leave() finished')


    def print(self):
        print(f"mode: {self.mode} (gossip_rate={self.gossip_rate})")
        print(f"is_introducer: {self.is_introducer}")
        self.mem_list.print()

    # def listener(self):
    #     '''listen to command line inputs '''
    #     while True:
    #         arg = input('--> ')
    #         if arg == 'print':
    #             print(f"mode: {self.mode} (gossip_rate={self.gossip_rate})")
    #             print(f"is_introducer: {self.is_introducer}")
    #             self.mem_list.print()
    #         elif arg == 'switch':
    #             self.switch()
    #         elif arg == 'join':
    #             self.join()
    #         elif arg =='joina2a':
    #             self.mode = "all_to_all"
    #             self.gossip_rate = 1
    #             self.join()
    #         elif arg == 'leave':
    #             self.leave()
    #         else:
    #             print('[ERROR] Invalid input argument %s' % arg)

    def run(self):
        threads = []
        workers = [self.sender, self.receiver, self.checker]
        for worker in workers:
            threads.append(threading.Thread(target=worker))
        for thread in threads:
            thread.start()

if __name__ == '__main__':
    s = MembershipServer()
    s.run()
