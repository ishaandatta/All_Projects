import time
import os
import json
import socket
import random
import threading
from collections import defaultdict

from logger import Logger
from membership import MembershipServer

from sdfs_utils import (
    SDFSFile,
    FileStatus,
    ErrorCode,
)

from constants import (
    DEFAULT_PORT_SDFS_NAMENODE,
    DEFAULT_PORT_SDFS_DATANODE,
    DEFAULT_PRIMARY_NAMENODE_HOST,
    DEFAULT_BACKUP_NAMENODE_HOSTS
)

from message import (
    MessageType, 
    Message
)

DEBUG = True

class NameNodeServer:
    def __init__(self, mem_server):
        self.host = socket.gethostname()
        self.addr = (self.host, DEFAULT_PORT_SDFS_NAMENODE)
        
        self.primary = False
        self.masterHost = DEFAULT_PRIMARY_NAMENODE_HOST
        self.masterAddr = (self.masterHost, DEFAULT_PORT_SDFS_NAMENODE)

        self.membershipList = mem_server
        self.fileTable = defaultdict(SDFSFile)
        self.activeHosts = []

        self.lock = threading.Lock()
        self.logger = Logger(name="NameNodeServer").logger

    def handleClientRequest(self, msg_type, sdfs_filename, local_filename = None):
        if self.primary:
            if DEBUG:
                print(f"[DEBUG-NameNode-handleClient] self is primary, process {msg_type}, local file: {local_filename}, sdfs file: {sdfs_filename}")
            if msg_type == 'put':
                self.handlePut(self.host, sdfs_filename, local_filename)
            elif msg_type == 'get':
                self.handleGet(self.host, sdfs_filename)
            elif msg_type == 'delete':
                self.handleDelete(self.host, sdfs_filename)
        else:
            if DEBUG:
                print(f"[DEBUG-NameNode-handleClient] self isn't primary, send to {self.masterHost} of message {msg_type}, local file: {local_filename}, sdfs file: {sdfs_filename}")
            sdfsFile = SDFSFile(sdfs_filename, local_filename)
            self.sendInstruction(self.masterHost, sdfsFile, msg_type, port = DEFAULT_PORT_SDFS_NAMENODE)

    def handlePut(self, put_host, sdfs_filename, local_filename):
        ''' Handle new put request by asking the vm calling the put to store 
        `local_filename` as `sdfs_filename` in its local sdfs path '''
        with self.lock:
            # Update file
            if sdfs_filename in self.fileTable:
                if DEBUG:
                    print(f"[DEBUG-NameNode-handlePut] {sdfs_filename} already in table")
                
                sdfsFile = self.fileTable[sdfs_filename]
                # Report error to host calling the delete request
                if sdfsFile.status in [FileStatus.PendingReplication, FileStatus.PendingUpload]:
                    dummyFile = SDFSFile('', '')
                    dummyFile.status = ErrorCode.FileNotReady
                    self.sendInstruction(put_host, dummyFile, MessageType.UPL_REQ)
                    return
                
                # Delete previous written file if existed
                if sdfsFile.status == FileStatus.Ready:
                    old_replicas = sdfsFile.replicas.copy()
                    for host in old_replicas:
                        self.sendInstruction(host, sdfsFile, MessageType.DEL_REQ)
                
                sdfsFile.update(local_filename)
                self.sendInstruction(put_host, sdfsFile, MessageType.UPL_REQ)

            # Put new file
            else:
                if DEBUG:
                    print(f"[DEBUG-NameNode-handlePut] {sdfs_filename} is a new file!")
                self.fileTable[sdfs_filename] = SDFSFile(sdfs_filename, local_filename)
                sdfsFile = self.fileTable[sdfs_filename]
                self.sendInstruction(put_host, sdfsFile, MessageType.UPL_REQ)

    def handleDelete(self, del_host, sdfs_filename):
        ''' Handle delete file request, by asking the vms holding the `sdfs_filename` file
        to delete that file from its local sdfs path '''
        with self.lock:
            # Report error to host calling the delete request
            if sdfs_filename not in self.fileTable:
                dummyFile = SDFSFile('', '')
                dummyFile.status = ErrorCode.FileNotFound
                self.sendInstruction(del_host, dummyFile, MessageType.DEL_REQ)

            # Report error to host calling the get request
            elif self.fileTable[sdfs_filename].status != FileStatus.Ready:
                sdfsFile = self.fileTable[sdfs_filename]
                dummyFile = SDFSFile('', '')
                if sdfsFile.status == FileStatus.Deleted:
                    dummyFile.status = ErrorCode.FileNotFound 
                else:
                    dummyFile.status = ErrorCode.FileNotReady
                self.sendInstruction(del_host, dummyFile, MessageType.DEL_REQ)

            # Send out delete instructions to replica vms
            else:
                sdfsFile = self.fileTable[sdfs_filename]
                old_replicas = sdfsFile.replicas.copy()
                sdfsFile.delete()
                for host in old_replicas:
                    self.sendInstruction(host, sdfsFile, MessageType.DEL_REQ)
        self.broadcast()

    def handleGet(self, get_host, sdfs_filename):
        ''' Handle get file request, by asking the get_host to copy file from one of 
        the replicas hosts '''
        with self.lock:
            # Report error to host calling the get request
            if sdfs_filename not in self.fileTable:
                dummyFile = SDFSFile('', '')
                dummyFile.status = ErrorCode.FileNotFound
                self.sendInstruction(get_host, dummyFile, MessageType.GET_REQ)

            # Report error to host calling the get request
            elif self.fileTable[sdfs_filename].status != FileStatus.Ready:
                sdfsFile = self.fileTable[sdfs_filename]
                dummyFile = SDFSFile('', '')
                if sdfsFile.status == FileStatus.Deleted:
                    dummyFile.status = ErrorCode.FileNotFound 
                else:
                    dummyFile.status = ErrorCode.FileNotReady 
                self.sendInstruction(get_host, dummyFile, MessageType.GET_REQ)

            # Send okay message to get_host to copy the requested file
            else:
                sdfsFile = self.fileTable[sdfs_filename]
                self.sendInstruction(get_host, sdfsFile, MessageType.GET_REQ)

    def handleNodeFail(self, failed_hosts):
        ''' reallocate file when node fails, given a list of failed hosts '''
        failed_hosts = set(failed_hosts)        

        # Loop through file table to check for impacted files
        for sdfsFile in self.fileTable.values():
            if sdfsFile.status == FileStatus.Deleted:
                continue
            elif set(sdfsFile.replicas).isdisjoint(failed_hosts) and \
                    set(sdfsFile.assigned).isdisjoint(failed_hosts):
                continue
            
            sdfsFile.replicas = list(set(sdfsFile.replicas) - failed_hosts)
            sdfsFile.assigned = list(set(sdfsFile.replicas) - failed_hosts)
                
            if len(sdfsFile.assigned) == 0:
                sdfsFile.status = FileStatus.Deleted
            else:
                sdfsFile.status = FileStatus.PendingReplication
                new_replicas = sdfsFile.assign_replicas(self.activeHosts)
                for host in new_replicas:
                    self.sendInstruction(host, sdfsFile, MessageType.REP_REQ)

    def updateFileStatus(self, host, filename, msg_type):
        ''' Need to define local file table update msg body format '''
        with self.lock:
            if msg_type == MessageType.REP_ACK:
                if DEBUG:
                    print(f"[DEBUG-NameNode-updateStatus] Update file table for REP_ACK")
                sdfsFile = self.fileTable[filename]
                sdfsFile.replicas.append(host)
                if sdfsFile.status == FileStatus.PendingReplication and \
                        len(sdfsFile.replicas) == 4:
                    if DEBUG:
                        print(f"[DEBUG-NameNode-updateStatus] Set file status from [{sdfsFile.status}] to [{FileStatus.Ready}]")
                    sdfsFile.status = FileStatus.Ready

            elif msg_type == MessageType.UPL_ACK:
                if DEBUG:
                    print(f"[DEBUG-NameNode-updateStatus] Update file table for UPL_ACK")
                sdfsFile = self.fileTable[filename]
                sdfsFile.assigned.append(host)
                sdfsFile.replicas.append(host)
                if sdfsFile.status == FileStatus.PendingUpload and \
                        len(sdfsFile.replicas) == 1:
                    if DEBUG:
                        print(f"[DEBUG-NameNode-updateStatus] Set file status from [{FileStatus.PendingUpload}] to [{FileStatus.PendingReplication}]")
                    sdfsFile.status = FileStatus.PendingReplication
                    new_replicas = sdfsFile.assign_replicas(self.activeHosts)
                    for host in new_replicas:
                        self.sendInstruction(host, sdfsFile, MessageType.REP_REQ)

        self.broadcast()

    def updateFiletable(self, newTable):
        with self.lock:
            for file in newTable:
                newFile = SDFSFile(newTable[file]["filename"], newTable[file]["local_filename"])
                newFile.assigned = newTable[file]["assigned"]
                newFile.replicas = newTable[file]["replicas"]
                newFile.status = newTable[file]["status"]
                newFile.version = newTable[file]["version"]
                newFile.sdfsname = newTable[file]["sdfsname"]
                self.fileTable[file] = newFile
            for file in self.fileTable:
                if file not in newTable:
                    del self.fileTable[file]

    def broadcast(self):
        with self.lock:
            active_vms = self.activeHosts.copy()
            active_vms.remove(self.host)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                dicts = {}
                temp_file_table = {}
                for f in self.fileTable:
                    temp_file_table[f] = self.fileTable[f].dictify()
                dicts['type'] = MessageType.FILE_TABLE
                dicts['from_vm'] = self.addr
                dicts['file_table'] = temp_file_table
                data = json.dumps(dicts).encode('UTF-8')

                for vm in active_vms:
                    to_vm = (vm, DEFAULT_PORT_SDFS_NAMENODE)
                    sock.sendto(data, to_vm)


    def sendInstruction(self, host, sdfsFile, msg_type, port = DEFAULT_PORT_SDFS_DATANODE):
        ''' send instruction to the target host '''
        to_vm = (host, port)
        if DEBUG:
            print(f"[DEBUG-NameNode-sendInstr] send message {msg_type} to address: {to_vm}")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            dicts = sdfsFile.dictify()
            dicts['from_vm'] = self.addr
            dicts['type'] = msg_type
            data = json.dumps(dicts).encode('UTF-8')

            sock.sendto(data, to_vm)
    
    def print_file(self, sdfs_filename):
        if sdfs_filename not in self.fileTable:
            return ErrorCode.FileNotFound
        self.fileTable[sdfs_filename].print()

    def checker(self):
        while True:
            time.sleep(1)
            ml = self.membershipList.mem_list
            with ml.lock:
                cur_active_hosts = [x.address[0] for x in ml.list.values()]
                
            with self.lock:
                # Get newest host
                if len(cur_active_hosts) >= 4 and self.masterHost not in cur_active_hosts:
                    self.masterHost = min(cur_active_hosts)
                    self.masterAddr = (self.masterHost, DEFAULT_PORT_SDFS_NAMENODE)

                # Check if self is the primary master
                self.primary = True if (self.masterAddr == self.addr) else False

                # Update active hosts based on the membership list
                prev_active_hosts = self.activeHosts.copy()
                self.activeHosts = cur_active_hosts
            
                # Check for failed nodes
                failed_hosts = set(prev_active_hosts) - set(self.activeHosts)
                if failed_hosts and self.primary:
                    if DEBUG:
                        print(f"[DEBUG-NameNode-nodeFail] Detected node failures: {failed_hosts}")
                        print(f"[DEBUG-NameNode-nodeFail] Previous active hosts: {prev_active_hosts}")
                        print(f"[DEBUG-NameNode-nodeFail] New active hosts: {self.activeHosts}")
                        ml.print()
                    self.handleNodeFail(failed_hosts)

    # receive updates on local files from data nodes
    def receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.addr)
        while True:
            data, _ = sock.recvfrom(8192)
            msg = json.loads(data.decode('UTF-8'))
            host = msg['from_vm'][0]

            if DEBUG:
                print(f"[DEBUG-NameNode-receiver] received message from {msg['from_vm']} of type {msg['type']}")

            # Client requests (from other non-primary name nodes)
            if msg['type'] == MessageType.PUT:
                local_filename = msg['local_filename']
                filename = msg['filename']
                self.handlePut(host, filename, local_filename)
            elif msg['type'] == MessageType.GET:
                filename = msg['filename']
                self.handleGet(host, filename)
            elif msg['type'] == MessageType.DELETE:
                filename = msg['filename']
                self.handleDelete(host, filename)
            # Datanode acknowledgement
            elif msg['type'] in [MessageType.REP_ACK, MessageType.UPL_ACK]:
                filename = msg['filename']
                self.updateFileStatus(host, filename, msg['type'])
            elif msg['type'] == MessageType.FILE_TABLE:
                self.updateFiletable(msg['file_table'])

    def run(self):
        threads = []
        workers = [self.receiver, self.checker]
        for worker in workers:
            threads.append(threading.Thread(target=worker))
        for thread in threads:
            thread.start()
        # for thread in threads:
        #     thread.join()