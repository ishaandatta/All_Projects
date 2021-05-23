import json
import time
import random
import threading
import math
from logger import Logger

class TimePeriod:
    ''' Time period constants in miliseconds '''
    SENDER_SLEEP = 25
    CHECKER_SLEEP = 50
    RECEIVER_SLEEP = 50
    FAIL_TIMEOUT = 650
    CLEANUP_TIMEOUT = 350

class Status:
    ''' Status code used in membership list entry `MembershipListEntry` '''
    NORMAL= 0
    FAILED= 1
    LEFT= 2
    PENDING = 3

INIT_HEARTBEAT = 0

def get_timestamp():
    ''' Helper function: get the time in milliseconds since the epoch as an interger '''
    return int(time.time() * 100)

class MembershipListEntry:
    def __init__(self, address, heartbeat = INIT_HEARTBEAT, status = Status.LEFT):
        self.address = address
        self.heartbeat = heartbeat
        self.status = status
        self.timestamp = get_timestamp()

    def increment(self):
        self.heartbeat += 1
        self.timestamp = get_timestamp()
    
    def check_failure(self):
        now = get_timestamp()
        # Suspect itself as "FAILED" if passed FAIL_TIMEOUT period
        if self.status == Status.NORMAL:
            if now - self.timestamp >= TimePeriod.FAIL_TIMEOUT:
                self.status = Status.FAILED
                self.timestamp = get_timestamp()
        
        # Confirm itself as "FAILED" if passed CLEANUP_TIMEOUT period
        if self.status in [Status.FAILED, Status.LEFT]:
            if now - self.timestamp >= TimePeriod.CLEANUP_TIMEOUT:
                return True
        return False

    def dict_repr(self):
        return self.__dict__


class MembershipList:
    def __init__(self, id, ip_address):
        self.id  = id
        self.ip_address = ip_address

        self.list = { id: MembershipListEntry(ip_address) }

        self.lock = threading.Lock()
        self.logging = Logger(name="MembershipList").logger

    def update(self, memlist):
        ''' Used by receiver to update membership list '''
        for id in memlist:
            if id == self.id:
                continue
            new_address = memlist[id]["address"]
            new_heartbeat = memlist[id]["heartbeat"]
            new_timestamp = memlist[id]["timestamp"]
            new_status = memlist[id]["status"]
            if new_status == Status.NORMAL:
                now = get_timestamp()
                if id not in self.list and now - new_timestamp <= TimePeriod.FAIL_TIMEOUT:
                    self.list[id] = MembershipListEntry(new_address, new_heartbeat, new_status)
                    self.list[id].timestamp = new_timestamp
                    self.logging.info(f'[Update] {new_address} has joined membership list')

                elif self.list[id].status == Status.NORMAL:
                    mle = self.list[id]
                    if mle.heartbeat < new_heartbeat:
                        mle.heartbeat = new_heartbeat
                        mle.timestamp = new_timestamp
                        #self.logging.info(f'[Heartbeat] {mle.address} has new heartbeat {new_heartbeat}')
    
    def check_and_delete(self):
        ''' Used by checker to check and delete expired failed/left nodes '''
        ids = list(self.list.keys())
        for id in ids:
            if id != self.id and self.list[id].check_failure():
                new_address = self.list[id].address
                del self.list[id]
                self.logging.info(f'[DELETE] failed/left {new_address} timeout and was removed from membership list.')

    def construct_message(self, gossip_rate = 1):
        ''' Used by sender to send messages to other nodes '''
        message = {k : v.dict_repr() for k, v in self.list.items()}
        alive_ids = [k for k in self.list.keys() \
                        if self.list[k].status == Status.NORMAL and k != self.id]
        n = len(alive_ids)
        if n == 0:
            addresses = []
        else:
            n = max(1, math.ceil(n * gossip_rate))
            selected_ids = set(random.sample(alive_ids, n))
            addresses = [v.address for k, v in self.list.items() if k in selected_ids]
        return addresses, message

    def print(self):
        print(f"addr: {self.ip_address[0]}:{self.ip_address[1]}")
        print(f"uuid: {self.id}")
        print("=" * 93)
        fmt = '{:<5} {:<40} {:<15} {:<15} {:<15}'
        print(fmt.format("ID", "IP Address", "Last Heartbeat", "Last Timestamp", "Status"))
        print(fmt.format("-" * 5 ,"-" * 40, "-" * 15, "-" * 15, "-" * 15))
        for key, x in self.list.items():
            address = x.address[0] + ":" + str(x.address[1])
            status = ["NORMAL", "FAILED", "LEFT", "PENDING"][x.status]
            print(fmt.format(key[-4:], address, str(x.heartbeat), str(x.timestamp), status))
