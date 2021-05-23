import os
import json
import shutil
import time
import socket
import subprocess
import threading
from paramiko import SSHClient
from scp import SCPClient

from logger import Logger

from sdfs_utils import (
    SDFSFile,
    FileStatus,
    ErrorCode,
)

from constants import (
    DEFAULT_PORT_SDFS_DATANODE,
    SDFS_PATH,
)

from credentials import (
    USERNAME,
    PASSWORD,
)

from message import (
    MessageType, 
    Message
)

DEBUG = True

class DataNodeServer:
    def __init__(self):
        self.host = socket.gethostname()
        self.addr = (self.host, DEFAULT_PORT_SDFS_DATANODE)
        self.logger = Logger(name="DataNodeServer").logger

    def handleUploadRequest(self, message):
        ''' Upload `local_filename` as `sdfs_filename` in local sdfs path '''
        if DEBUG:
            print(f"[DEBUG-DataNode-handleUpload] received a Upload request from master {message['from_vm']}")

        status = message['status']
        sdfs_filename = message['sdfsname']
        local_filename = message['local_filename']

        if status in [ErrorCode.FileNotFound, ErrorCode.FileNotReady]:
            print(f"[ERROR-DataNode-handleUpload] Requested file: {sdfs_filename} Error: {status}")
            return status

        if not os.path.exists(local_filename):
            print(f'[ERROR-DataNode-handleUpload] Requested file: {local_filename} Error: {ErrorCode.FileNotFound}')
            return ErrorCode.FileNotFound
    
        shutil.copyfile(local_filename, os.path.join(SDFS_PATH, sdfs_filename))
        self.sendAcknowledgement(message, MessageType.UPL_ACK)
        return ErrorCode.Normal

    def handleDeleteRequest(self, message):
        ''' Delete `sdfs_filename` from local sdfs path '''
        if DEBUG:
            print(f"[DEBUG-DataNode-handleDel] received a Delete request from master {message['from_vm']}")
        
        status = message['status']
        sdfs_filename = message['sdfsname']
        sdfs_filepath = os.path.join(SDFS_PATH, sdfs_filename)

        if status in [ErrorCode.FileNotFound, ErrorCode.FileNotReady]:
            print(f"[Error-DataNode-handleDel] Requested file: {sdfs_filename} Error: {status}")
            return status
            
        if os.path.isfile(sdfs_filepath):
            if DEBUG:
                print(f'[DEBUG-DataNode-handleDel] deleted file {sdfs_filename}')
            os.remove(sdfs_filepath)
        return ErrorCode.Normal

    def handleGetRequest(self, message):
        ''' Get `sdfs_filename` from replica vms to local path '''
        if DEBUG:
            print(f"[DEBUG-DataNode-handleGet] received a Get request for file {message['sdfsname']}")
        
        status = message['status']
        replica_hosts = message['replicas']
        filename = message['filename']
        sdfs_filename = message['sdfsname']
        sdfs_filepath = os.path.join(SDFS_PATH, sdfs_filename)

        if status in [ErrorCode.FileNotFound, ErrorCode.FileNotReady]:
            print(f"[Error-DataNode-handleGet] Requested file: {filename} Error: {status}")
            return status

        if self.host in replica_hosts:
            shutil.copyfile(sdfs_filepath, filename)
        else:
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.connect(hostname = replica_hosts[0],
                        username = USERNAME,
                        password = PASSWORD)

            while filename not in os.listdir('.'):
                try:
                    with SCPClient(ssh.get_transport()) as scp:
                        scp.get(sdfs_filepath, filename)
                except:
                    pass

        filename_size = os.path.getsize(filename)
        print(f"[INFO-DataNode-handleGet] [{sdfs_filename}] successfully saved as [{filename}] of size [{filename_size}]")
        return ErrorCode.Normal

    def handleReplicateRequest(self, message):
        ''' Copy `sdfs_filename` from replica_vm's sdfs path to local sdfs path '''
        if DEBUG:
            print(f"[DEBUG-DataNode-handleRep] received a Replica request from master {message['from_vm']}")
        
        replica_hosts = message['replicas']
        sdfs_filename = message['sdfsname']
        sdfs_filepath = os.path.join(SDFS_PATH, sdfs_filename)

        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(hostname = replica_hosts[0],
                    username = USERNAME,
                    password = PASSWORD)

        while sdfs_filename not in os.listdir(os.path.expanduser(SDFS_PATH)):
            try:
                with SCPClient(ssh.get_transport()) as scp:
                    scp.get(sdfs_filepath, sdfs_filepath)
            except:
                pass

        self.sendAcknowledgement(message, MessageType.REP_ACK)
        return ErrorCode.Normal

    def sendAcknowledgement(self, message, msg_type):
        if DEBUG:
            print(f"[DEBUG-DataNode-sendAck] sent a ACK {msg_type} to master {message['from_vm']}")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            dicts = {
                'filename': message['filename'],
                'from_vm': self.addr,
                'type': msg_type
                }
            data = json.dumps(dicts).encode('UTF-8')
            namenode_vm = tuple(message['from_vm'])
            sock.sendto(data, namenode_vm)

    def print(self):
        # Print all local sdfs files 
        print(f"SDFS Dir: {SDFS_PATH}")
        print("=" * 21)
        fmt = '{:<5} {:<15}'
        print(fmt.format("No.", "SDFS File Name"))
        print(fmt.format("-" * 5 ,"-" * 15))
        counter = 1
        sdfs_dir = os.path.expanduser(SDFS_PATH)
        for file in os.listdir(sdfs_dir):
            print(fmt.format(counter, file))
            counter += 1

    # receive updates on local files from data nodes
    def receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.addr)
        while True:
            data, _ = sock.recvfrom(4096)
            msg = json.loads(data.decode('UTF-8'))

            if DEBUG:
                print(f"[DEBUG-DataNode-receiver] received message from {msg['from_vm']} of type {msg['type']}")

            if msg['type'] == MessageType.REP_REQ:
                thread = threading.Thread(target=self.handleReplicateRequest, args=(msg,))
                #self.handleReplicateRequest(msg)
            elif msg['type'] == MessageType.UPL_REQ:
                thread = threading.Thread(target=self.handleUploadRequest, args=(msg,))
                #self.handleUploadRequest(msg)
            elif msg['type'] == MessageType.DEL_REQ:
                thread = threading.Thread(target=self.handleDeleteRequest, args=(msg,))
                #self.handleDeleteRequest(msg)
            elif msg['type'] == MessageType.GET_REQ:
                thread = threading.Thread(target=self.handleGetRequest, args=(msg,))
                #self.handleGetRequest(msg)
            thread.start()

    def clear_sdfs_files(self):
        if os.path.exists(SDFS_PATH):
            shutil.rmtree(SDFS_PATH)
        os.mkdir(SDFS_PATH)

    def run(self):
        # Delete pre-existing files on initialization
        self.clear_sdfs_files()

        threads = []
        workers = [self.receiver,]
        for worker in workers:
            threads.append(threading.Thread(target=worker))
        for thread in threads:
            thread.start()
        # for thread in threads:
        #     thread.join()

if __name__ == '__main__':
    s = DataNodeServer()