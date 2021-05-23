import os
import json
import shutil
import time
import socket
import subprocess
import threading
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
from collections import defaultdict
from logger import Logger

from sdfs_utils import (
    SDFSFile,
    FileStatus,
    ErrorCode,
)

from maplejuice_utils import (
    Job,
    JobStatus,
    Task,
    TaskStatus,
    TaskType,
    # ErrorCodeMJ,
)

from constants import (
    DEFAULT_PORT_MJ_DATANODE,
    SDFS_PATH,
    TMP_PATH,
)

from credentials import (
    USERNAME,
    PASSWORD,
)

from message import (
    MessageType, 
    Message
)

DEBUG = False

class DataNodeServer:
    def __init__(self):
        self.host = socket.gethostname()
        self.addr = (self.host, DEFAULT_PORT_MJ_DATANODE)
        self.logger = Logger(name="MJDataNodeServer").logger

    def handleJob(self, message):
        ''' Receives a job and get the mj_exe to local directory '''
        mj_exe = message['mj_exe']
        from_vm = message['from_vm']

        if DEBUG:
            print(f"[DEBUG-MJDataNode-handleJob] {from_vm} {mj_exe}")

        # Get mj_exe from master
        ssh = SSHClient()
        ssh.load_system_host_keys()
        # ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(hostname = from_vm[0],
                    username = USERNAME,
                    password = PASSWORD)

        mj_exe_path = os.path.join(TMP_PATH, mj_exe)
        remote_path = os.path.join('mp3', mj_exe_path)
        while mj_exe not in os.listdir(TMP_PATH):
            time.sleep(1)
            try:
                with SCPClient(ssh.get_transport()) as scp:
                    scp.get(remote_path, mj_exe_path)
            except Exception as e:
                print(e)
                stdin, stdout, stderr=ssh.exec_command("ls")
                print(stdout.readlines())
                print(stderr.readlines())
                pass

        filename_size = os.path.getsize(mj_exe_path)
        print(f"[INFO-DataNode-handleJob] [{mj_exe}] successfully saved as [{mj_exe_path}] of size [{filename_size}]")

        self.sendAcknowledgement(message, MessageType.JOB_ACK)
        return ErrorCode.Normal

    def handleMapleTask(self, message):
        ''' Receives maple task and perform calculations on data '''
        print(f'[DEBUG-DataNode-handleMapleTask]')
        mj_exe = message['mj_exe']
        if mj_exe not in os.listdir('.'):
            if DEBUG:
                print(f"[DEBUG-DataNode-handleMapleTask] {mj_exe} does not exist in handleMapleTask()")
            return

        data = ''.join(message['data'])
        message['data'] = []

        # subprocess
        with subprocess.Popen(["python3", mj_exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            output = proc.communicate(input=data.encode())[0]
            output = output.decode()
            message['kvpairs'] = defaultdict(list)

            for line in output.rstrip('\n').split('\n'):
                if line:
                    k = line.split(' ')[0]
                    v = line.split(' ')[1]
                    message['kvpairs'][k].append(v)

        message['status'] = TaskStatus.PendingUpload
        self.sendAcknowledgement(message, MessageType.TASK_ACK)

    def handleJuiceTask(self, message):
        ''' Receives juice task and perform calculations on data '''
        ''' Receives maple task and perform calculations on data '''
        mj_exe = message['mj_exe']
        from_vm = message['from_vm']
        if mj_exe not in os.listdir(TMP_PATH):
            if DEBUG:
                print(f"[DEBUG-DataNode-handleJuiceTask] {mj_exe} does not exist in handleMapleTask()")
            
            # Get mj_exe from master
            ssh = SSHClient()
            ssh.load_system_host_keys()
            # ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(hostname = from_vm[0],
                        username = USERNAME,
                        password = PASSWORD)

            mj_exe_path = os.path.join(TMP_PATH, mj_exe)
            remote_path = os.path.join('mp3', mj_exe_path)
            while mj_exe not in os.listdir(TMP_PATH):
                time.sleep(1)
                try:
                    with SCPClient(ssh.get_transport()) as scp:
                        scp.get(remote_path, mj_exe_path)
                except Exception as e:
                    print(e)
                    stdin, stdout, stderr=ssh.exec_command("ls")
                    print(stdout.readlines())
                    print(stderr.readlines())
                    pass

            filename_size = os.path.getsize(mj_exe_path)
            print(f"[INFO-DataNode-handleJuiceTask] [{mj_exe}] successfully saved as [{mj_exe_path}] of size [{filename_size}]")

        juice_file = message['data']

        # Get mj_exe from master
        ssh = SSHClient()
        ssh.load_system_host_keys()
        # ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(hostname = from_vm[0],
                    username = USERNAME,
                    password = PASSWORD)

        juice_file_path = os.path.join(TMP_PATH, juice_file)
        remote_path = os.path.join('mp3', juice_file_path)
        while juice_file not in os.listdir(TMP_PATH):
            try:
                with SCPClient(ssh.get_transport()) as scp:
                    scp.get(remote_path, juice_file_path)
            except Exception as e:
                print(e)
                stdin, stdout, stderr=ssh.exec_command("ls")
                print(stdout.readlines())
                print(stderr.readlines())
                pass

        filename_size = os.path.getsize(juice_file_path)
        print(f"[INFO-DataNode-handleJob] [{juice_file}] successfully saved as [{juice_file_path}] of size [{filename_size}]")

        with open(juice_file_path, 'r') as f:
            # subprocess
            with subprocess.Popen(["python3", mj_exe], stdin=f, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
                output = proc.stdout.read().decode()
                print(output)
                message['key'] = juice_file.split('#')[1]
                message['result'] = output.rstrip('\n')

            message['status'] = TaskStatus.PendingUpload
            self.sendAcknowledgement(message, MessageType.TASK_ACK)

    def sendAcknowledgement(self, message, msg_type):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            namenode_vm = tuple(message['from_vm'])
            message['from_vm'] = self.addr
            message['type'] = msg_type
            message['timestamp'] = time.time()
            data = json.dumps(message).encode('UTF-8')
            sock.sendto(data, namenode_vm)

        if DEBUG:
            print(f"[DEBUG-MJDataNode-sendAck] sent a {msg_type} ACK of size {len(data)} to master {message['from_vm']}")

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
            data, _ = sock.recvfrom(16384)
            msg = json.loads(data.decode('UTF-8'))

            if DEBUG:
                print(f"[DEBUG-MJDataNode-receiver] received message from {msg['from_vm']} of type {msg['type']}")

            if msg['type'] == MessageType.TASK:
                if (msg['task_type'] == TaskType.Maple):
                    thread = threading.Thread(target=self.handleMapleTask, args=(msg,))
                    thread.start()
                elif (msg['task_type'] == TaskType.Juice):
                    # thread = threading.Thread(target=self.handleJuiceTask, args=(msg,))
                    self.handleJuiceTask(msg)
                #self.handleReplicateRequest(msg)
            elif msg['type'] == MessageType.JOB:
                thread = threading.Thread(target=self.handleJob, args=(msg, ))
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