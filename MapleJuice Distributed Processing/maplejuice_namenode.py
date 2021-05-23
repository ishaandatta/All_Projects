import time
import os
import json
import socket
import random
import threading
import shutil
from collections import defaultdict
import subprocess
import threading
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

from logger import Logger
from membership import MembershipServer

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

from credentials import (
    USERNAME,
    PASSWORD,
)

from constants import (
    DEFAULT_PORT_MJ_NAMENODE,
    DEFAULT_PORT_MJ_DATANODE,
    DEFAULT_PRIMARY_NAMENODE_HOST,
    DEFAULT_BACKUP_NAMENODE_HOSTS,
    MAPLE_BLOCK_SIZE,
    SDFS_PATH,
    TMP_PATH,
)

from message import (
    MessageType, 
    Message
)

DEBUG = False

class NameNodeServer:
    def __init__(self, mem_server, sdfs_namenode):
        self.host = socket.gethostname()
        self.addr = (self.host, DEFAULT_PORT_MJ_NAMENODE)
        
        self.primary = False
        self.masterHost = DEFAULT_PRIMARY_NAMENODE_HOST
        self.masterAddr = (self.masterHost, DEFAULT_PORT_MJ_NAMENODE)

        self.membershipList = mem_server
        self.sdfs_namenode = sdfs_namenode
        self.activeHosts = []

        self.lock = threading.Lock()
        self.logger = Logger(name="MJNameNodeServer").logger

        self.jobList = []

        if os.path.isdir('tmp'):
            shutil.rmtree('tmp')
        
        os.mkdir('tmp')


    def handleClientRequest(self, msg_type, mj_exe, num_workers, sdfs_prefix, sdfs_src_file, delete_input=False):
        if self.primary:
            if DEBUG:
                print(f"[DEBUG-MJNameNode-handleClient] self is primary, process {msg_type}, MJ executable: {mj_exe}, number of workers: {num_workers}, sdfs intermediate prefix: {sdfs_prefix}, sdfs location: {sdfs_src_file}, delete input: {delete_input}")
            if msg_type == 'maple':
                self.handleMaple(self.host, mj_exe, num_workers, sdfs_prefix, sdfs_src_file)
            elif msg_type == 'juice':
                self.handleJuice(self.host, mj_exe, num_workers, sdfs_prefix, sdfs_src_file, delete_input)
        else:
            if DEBUG:
                print(f"[DEBUG-MJNameNode-handleClient] self isn't primary, send to {self.masterHost} of message {msg_type}, MJ executable: {mj_exe}, number of workers: {num_workers}, sdfs intermediate prefix: {sdfs_prefix}, sdfs location: {sdfs_src_file}, delete input: {delete_input}")
            
            job = Job(mj_exe, num_workers, sdfs_prefix, sdfs_src_file)
            self.sendInstruction(self.masterHost, job, msg_type, port=DEFAULT_PORT_MJ_NAMENODE)

    def handleMaple(self, maple_host, mj_exe, num_maples, sdfs_prefix, sdfs_src_file):
        ''' handle maple requests from client (or other non-master nodes) '''
        with self.lock:
            maple_start_time = time.time()
            if DEBUG:
                print(f"[DEBUG-MJNameNode-handleMaple] master received maple message, MJ executable: {mj_exe}, number of workers: {num_maples}, sdfs intermediate prefix: {sdfs_prefix}, sdfs location: {sdfs_src_file}")
            
            if maple_host == self.host:
                mj_exe_path = os.path.join(TMP_PATH, mj_exe)
                sdfs_src_file_path = os.path.join(TMP_PATH, sdfs_src_file)
                shutil.copy(mj_exe, mj_exe_path)
                shutil.copy(sdfs_src_file, sdfs_src_file_path)
            else:
            # 2. Get sdfs_src_file to local dir if it's remote
            # self.nameNode.handleClientRequest(MessageType.GET, sdfs_src_file)
                ssh = SSHClient()
                ssh.load_system_host_keys()
                # ssh.set_missing_host_key_policy(AutoAddPolicy())
                # TODO: !!! Assuming maple initializer have mj_exe in its SDFS folder
                ssh.connect(hostname = maple_host,
                            username = USERNAME,
                            password = PASSWORD)

                mj_exe_path = os.path.join(TMP_PATH, mj_exe)
                remote_mj_exe_path = os.path.join('mp3', mj_exe)
                sdfs_src_file_path = os.path.join(TMP_PATH, sdfs_src_file)
                remote_sdfs_src_file_path = os.path.join('mp3', sdfs_src_file)

                # Save mj_exe to tmp
                while mj_exe not in os.listdir(TMP_PATH):
                    try:
                        with SCPClient(ssh.get_transport()) as scp:
                            scp.get(remote_mj_exe_path, mj_exe_path)
                    except Exception as e:
                        print(e)
                        stdin, stdout, stderr=ssh.exec_command("ls")
                        print(stdout.readlines())
                        print(stderr.readlines())
                        pass

                # Save sdfs_src_file to tmp
                while sdfs_src_file not in os.listdir(TMP_PATH):
                    try:
                        with SCPClient(ssh.get_transport()) as scp:
                            scp.get(remote_sdfs_src_file_path, sdfs_src_file_path)
                    except:
                        pass

            # 3. Schedules the job
            # 3. Push the job to job queue
            self.jobList.append(Job(mj_exe, num_maples, sdfs_prefix, sdfs_src_file))
            self.jobList[0].maple_start_time = maple_start_time

    # TODO: finish this function
    def scheduler(self):
        ''' regularly checks job list and schedule tasks to active nodes '''
        while True:
            time.sleep(3)
            if self.primary == False or len(self.jobList) == 0:
                continue

            with self.lock:
                job = self.jobList[0]

                # 1. if the job is pending, ask nodes to get mj_exe
                if (job.status == JobStatus.Initialize):
                    print(f"[DEBUG-MJNameNode-scheduler] Initialize")
                    # a. Get the workers for this job
                    if len(self.activeHosts) <= job.num_workers:
                        job.workers = self.activeHosts
                        job.num_workers = len(job.workers)
                    else:
                        job.workers = self.activeHosts[0:job.num_workers-1]
                    
                    # c. set job status
                    job.status = JobStatus.Prepare

                    # b. Ask worker to get mj_exe in its local directory
                    for worker in job.workers:
                        self.sendInstruction(worker, job, MessageType.JOB, DEFAULT_PORT_MJ_DATANODE)

                elif (job.status == JobStatus.Prepare):
                    print(f"[DEBUG-MJNameNode-scheduler] Prepare, workers {self.jobList[0].workers}, ready_workers {self.jobList[0].ready_workers}")
                    pass

                # 2. schedule tasks and ask nodes to do them.
                elif (job.status == JobStatus.PendingMaple):
                    print(f"[DEBUG-MJNameNode-scheduler] PendingMaple")
                    job.assignMapleTask()

                    # send maple tasks to nodes
                    for task in job.tasks:
                        self.sendInstruction(task.worker, task, MessageType.TASK, DEFAULT_PORT_MJ_DATANODE)
                        task.status = TaskStatus.Assigned
                        time.sleep(0.01)

                    job.status = JobStatus.RunningMaple
                    
                # 3. if job is running, see if there are any failed nodes in job 
                # (should be marked failed by checker and handleNodeFail already), 
                # and reschedules the tasks to other alive nodes.
                elif (job.status == JobStatus.RunningMaple):
                    print(f"[DEBUG-MJNameNode-scheduler] RunningMaple")
                    print(f"{len(job.finished_tasks)}/{len(job.tasks)}")
                    pass

                # 4. combine maple output / or sort?
                elif (job.status == JobStatus.CombiningMaple):
                    print(f"[DEBUG-MJNameNode-scheduler] CombiningMaple")
                    pass
                    
                elif (job.status == JobStatus.PendingJuice):
                    print(f"[DEBUG-MJNameNode-scheduler] PendingJuice")
                    pass

                elif (job.status == JobStatus.RunningJuice):
                    print(f"[DEBUG-MJNameNode-scheduler] RunningJuice")
                    # print(job.tasks)
                    # print(job.finished_tasks)
                    pass

                elif (job.status == JobStatus.Done):
                    print(f"[DEBUG-MJNameNode-scheduler] Done")
                    print(f"Maple Time: {job.maple_end_time - job.maple_start_time}")
                    print(f"Juice Time: {job.juice_end_time - job.juice_start_time}")
                    self.jobList = []
                    pass

    def handleJuice(self, juice_host, mj_exe, num_workers, sdfs_prefix, sdfs_dest_filename, delete_input=False):
        juice_start_time = time.time()
        if juice_host == self.host:
            mj_exe_path = os.path.join(TMP_PATH, mj_exe)
            shutil.copy(mj_exe, mj_exe_path)
        else:
        # 2. Get sdfs_src_file to local dir if it's remote
        # self.nameNode.handleClientRequest(MessageType.GET, sdfs_src_file)
            ssh = SSHClient()
            ssh.load_system_host_keys()
            # ssh.set_missing_host_key_policy(AutoAddPolicy())
            # TODO: !!! Assuming maple initializer have mj_exe in its SDFS folder
            ssh.connect(hostname = juice_host,
                        username = USERNAME,
                        password = PASSWORD)

            mj_exe_path = os.path.join(TMP_PATH, mj_exe)
            remote_mj_exe_path = os.path.join('mp3', mj_exe)

            # Save mj_exe to tmp
            while mj_exe not in os.listdir(TMP_PATH):
                try:
                    with SCPClient(ssh.get_transport()) as scp:
                        scp.get(remote_mj_exe_path, mj_exe_path)
                except Exception as e:
                    print(e)
                    stdin, stdout, stderr=ssh.exec_command("ls")
                    print(stdout.readlines())
                    print(stderr.readlines())
                    pass

        job = self.jobList[0]
        if job.status == JobStatus.PendingJuice:
            job.mj_exe = mj_exe
            job.sdfs_src_file = sdfs_dest_filename
            job.num_workers = num_workers

            if os.path.isfile(sdfs_dest_filename):
                os.remove(sdfs_dest_filename)

            if len(self.activeHosts) <= job.num_workers:
                job.workers = self.activeHosts
                job.num_workers = len(job.workers)
            else:
                job.workers = self.activeHosts[0:int(job.num_workers)-1]

            job.assignJuiceTask()



            for task in job.tasks:
                self.sendInstruction(task.worker, task, MessageType.TASK, DEFAULT_PORT_MJ_DATANODE)
                time.sleep(0.02)
                task.status = TaskStatus.Assigned

            job.status = JobStatus.RunningJuice
            job.juice_start_time = juice_start_time

    # TODO: Reallocate failed tasks to other active nodes
    # def handleNodeFail(self, failed_hosts):
    #     ''' reallocate file when node fails, given a list of failed hosts '''
    #     failed_hosts = set(failed_hosts)        

    #     # Loop through file table to check for impacted files
    #     for sdfsFile in self.fileTable.values():
    #         if sdfsFile.status == FileStatus.Deleted:
    #             continue
    #         elif set(sdfsFile.replicas).isdisjoint(failed_hosts) and \
    #                 set(sdfsFile.assigned).isdisjoint(failed_hosts):
    #             continue
            
    #         sdfsFile.replicas = list(set(sdfsFile.replicas) - failed_hosts)
    #         sdfsFile.assigned = list(set(sdfsFile.replicas) - failed_hosts)
                
    #         if len(sdfsFile.assigned) == 0:
    #             sdfsFile.status = FileStatus.Deleted
    #         else:
    #             sdfsFile.status = FileStatus.PendingReplication
    #             new_replicas = sdfsFile.assign_replicas(self.activeHosts)
    #             for host in new_replicas:
    #                 self.sendInstruction(host, sdfsFile, MessageType.REP_REQ)
 
    def updateJobStatus(self, host, status):
        ''' updates job status whenever a JOB_ACK is received '''
        if DEBUG:
            print(f"[DEBUG-MJNameNode-updateJobStatus] {host} {status}")

        with self.lock:
            if (status == JobStatus.Prepare):
                if host not in self.jobList[0].ready_workers:
                    self.jobList[0].ready_workers.append(host)
                if (set(self.jobList[0].ready_workers) == set(self.jobList[0].workers)):
                    self.jobList[0].status = JobStatus.PendingMaple

    def updateTaskStatus(self, tid, sdfs_prefix, kvpairs):
        ''' updates task status whenever a TASK_ACK is received '''
        if DEBUG:
            print(f"[DEBUG-MJNameNode-updateTaskStatus] {tid}")

        # write packet returned result to intermediate file
        for k in kvpairs.keys():
            # map intermediate result filename
            intermediate_file_path = sdfs_prefix + '#' + k
            intermediate_file_path = os.path.join('tmp', intermediate_file_path)
            
            # write to file
            with open(intermediate_file_path, 'a') as f:
                for v in kvpairs[k]:
                    f.write(f"{v}\n")

        # update current job status
        with self.lock:
            job = self.jobList[0]
            job.tasks[tid].status = TaskStatus.Done
            job.finished_tasks[tid] = True
            if len(job.finished_tasks) == len(job.tasks):
                # job.status = JobStatus.CombiningMaple
                job.status = JobStatus.PendingJuice
                job.maple_end_time = time.time()

    def updateTaskStatus2(self, tid, sdfs_prefix, result, data):
        ''' updates task status whenever a TASK_ACK is received '''
        if DEBUG:
            print(f"[DEBUG-MJNameNode-updateTaskStatus2] {tid}")

        with self.lock:
            job = self.jobList[0]
            sdfs_dest_filename = job.sdfs_src_file

        with open(sdfs_dest_filename, 'a') as f:
            key = data.split('#')[1]
            f.write(f"{key} {result}\n")

        # update current job status
        with self.lock:
            job = self.jobList[0]
            job.tasks[tid].status = TaskStatus.Done
            job.finished_tasks[tid] = True
            if len(job.finished_tasks) == len(job.tasks):
                job.status = JobStatus.Done
                job.juice_end_time = time.time()

    def sendInstruction(self, host, data, msg_type, port):
        ''' send instruction to the target host '''
        to_vm = (host, port)
        if DEBUG:
            print(f"[DEBUG-MJNameNode-sendInstr] send message {msg_type} to address: {to_vm}")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            message = data.dictify()
            message['from_vm'] = self.addr
            message['type'] = msg_type
            message['timestamp'] = time.time()
            body = json.dumps(message).encode('UTF-8')

            sock.sendto(body, to_vm)

    def checker(self):
        while True:
            time.sleep(1)
            ml = self.membershipList.mem_list
            with ml.lock:
                cur_active_hosts = [x.address[0] for x in ml.list.values()]
                
            with self.lock:
                # Get newest host (DON'T need to)
                if len(cur_active_hosts) >= 4 and self.masterHost not in cur_active_hosts:
                    self.masterHost = min(cur_active_hosts)
                    self.masterAddr = (self.masterHost, DEFAULT_PORT_MJ_NAMENODE)

                # Check if self is the primary master (DON'T need to)
                self.primary = True if (self.masterAddr == self.addr) else False

                # Update active hosts based on the membership list
                prev_active_hosts = self.activeHosts.copy()
                self.activeHosts = cur_active_hosts
            
                # Check for failed nodes
                failed_hosts = set(prev_active_hosts) - set(self.activeHosts)
                if failed_hosts and self.primary:
                    if DEBUG:
                        print(f"[DEBUG-MJNameNode-nodeFail] Detected node failures: {failed_hosts}")
                        print(f"[DEBUG-MJNameNode-nodeFail] Previous active hosts: {prev_active_hosts}")
                        print(f"[DEBUG-MJNameNode-nodeFail] New active hosts: {self.activeHosts}")
                        ml.print()
                    # self.handleNodeFail(failed_hosts)

    # TODO: Modify this function for MapReduce jobs/tasks
    # receive updates on local files from data nodes
    def receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.addr)
        while True:
            data, _ = sock.recvfrom(16384)
            msg = json.loads(data.decode('UTF-8'))
            host = msg['from_vm'][0]

            if DEBUG:
                print(f"[DEBUG-NameNode-receiver] received message from {msg['from_vm']} of type {msg['type']}")

            # Client requests (from other non-primary name nodes)
            if msg['type'] == MessageType.MAPLE:
                mj_exe = msg['mj_exe']
                num_maples = msg['num_workers']
                sdfs_prefix = msg['sdfs_prefix']
                sdfs_src_file = msg['sdfs_src_file']
                # thread = threading.Thread(target=self.handleMaple, args=(host, mj_exe, num_maples, sdfs_prefix, sdfs_src_file,))
                # thread.start()
                self.handleMaple(host, mj_exe, num_maples, sdfs_prefix, sdfs_src_file)
            elif msg['type'] == MessageType.JUICE:
                mj_exe = msg['mj_exe']
                num_juices = msg['num_workers']
                sdfs_prefix = msg['sdfs_prefix']
                sdfs_src_file = msg['sdfs_src_file']
                # delete_input = msg['delete_input']
                # thread = threading.Thread(target=self.handleJuice, args=(host, mj_exe, num_juices, sdfs_prefix, sdfs_src_file,))
                # thread.start()
                self.handleJuice(host, mj_exe, num_juices, sdfs_prefix, sdfs_src_file)

            # Datanode acknowledgement
            elif msg['type'] == MessageType.JOB_ACK:
                self.updateJobStatus(host, msg['status'])

            elif msg['type'] == MessageType.TASK_ACK:
                if msg['task_type'] == TaskType.Maple:
                    thread = threading.Thread(target=self.updateTaskStatus, args=(msg['tid'], msg['sdfs_prefix'], msg['kvpairs'],))
                    thread.start()
                    # self.updateTaskStatus(msg['tid'], msg['sdfs_prefix'], msg['kvpairs'])
                elif msg['task_type'] == TaskType.Juice:
                    thread = threading.Thread(target=self.updateTaskStatus2, args=(msg['tid'], msg['sdfs_prefix'], msg['result'], msg['data'],))
                    thread.start()
                    # self.updateTaskStatus2(msg['tid'], msg['sdfs_prefix'], msg['result'], msg['data'])

    # TODO: Modify this function for MapReduce jobs/tasks
    def run(self):
        threads = []
        workers = [self.receiver, self.checker, self.scheduler]
        for worker in workers:
            threads.append(threading.Thread(target=worker))
        for thread in threads:
            thread.start()
        # for thread in threads:
        #     thread.join()