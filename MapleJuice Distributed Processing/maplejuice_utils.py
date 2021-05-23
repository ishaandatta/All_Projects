import os
import sys
import json
import random
from collections import defaultdict

from constants import (
    MAPLE_BLOCK_SIZE,
    SDFS_PATH,
    TMP_PATH,
)

DEBUG = True

class TaskStatus:
    PendingAssign = "pending_assign"
    Assigned = "assigned"
    PendingUpload = "pending_upload"
    PendingCombine = "pending_combine"
    Done = "done"

class TaskType:
    Maple = "maple"
    Juice = "juice"
    JobSetup = "job_setup"
    JobCleanup = "job_cleanup"
    TaskCleanup = "task_cleanup"

class Task:
    def __init__(self, task_type, mj_exe, tid, sdfs_prefix, worker):
        self.task_type = task_type
        self.mj_exe = mj_exe
        self.tid = tid
        self.sdfs_prefix = sdfs_prefix
        self.worker = worker
        self.status = TaskStatus.PendingAssign
        self.data = []
        self.kvpairs = {}
    
    def dictify(self):
        dicts = {
            'task_type': self.task_type,
            'mj_exe': self.mj_exe,
            'tid': self.tid,
            'sdfs_prefix': self.sdfs_prefix,
            'worker': self.worker,
            'status': self.status,
            'data': self.data,
            'kvpairs': self.kvpairs,
        }
        return dicts

class JobStatus:
    # fileStatus: pendingUpload, pendingReplication, ready, pendingDelete, deleted, pendingChange
    Initialize = "initialize"
    Prepare = "prepare"
    PendingMaple = "pending_maple"
    RunningMaple = "running_maple"
    CombiningMaple = "combining_maple"
    PendingJuice = "pending_juice"
    RunningJuice = "running_juice"
    Done = "done"

class Job:
    def __init__(self, mj_exe, num_workers, sdfs_prefix, sdfs_src_file):
        self.mj_exe = mj_exe
        self.num_workers = int(num_workers)
        self.sdfs_prefix = sdfs_prefix
        self.sdfs_src_file = sdfs_src_file
        self.status = JobStatus.Initialize
        self.workers = []
        self.ready_workers = []
        self.tasks = []
        self.finished_tasks = defaultdict(bool)

    def dictify(self):
        dicts = {
            'status': self.status,
            'num_workers': self.num_workers,
            'sdfs_prefix': self.sdfs_prefix,
            'sdfs_src_file': self.sdfs_src_file,
            'mj_exe': self.mj_exe,
            'workers': self.workers,
            'tasks' : self.tasks,
        }
        return dicts

    def assignMapleTask(self, hash_or_range=False):
        num_lines = 0
        if DEBUG:
            print(f"DEBUG-MJUtils-assignMapleTask")
        with open(self.sdfs_src_file, 'r') as f:
            for _ in f:
                num_lines += 1
            f.seek(0)

            tid_counter = 0
            while (num_lines > 0):
                for i in range(len(self.workers)):
                    # make a new task if still need to read lines from src file
                    task = Task(TaskType.Maple, self.mj_exe, tid_counter, self.sdfs_prefix, self.workers[i])
                    tid_counter += 1
                    curr = MAPLE_BLOCK_SIZE
                    # assign lines to current task
                    while (curr > 0 and num_lines > 0):
                        task.data.append(f.readline())
                        curr -= 1
                        num_lines -= 1
                    self.tasks.append(task)
    
    def assignJuiceTask(self, hash_or_range=False):
        self.tasks = []
        self.finished_tasks = defaultdict(bool)

        tid_counter = 0
        for filename in os.listdir(TMP_PATH):
            print(filename)
            print(filename[:len(self.sdfs_prefix)], self.sdfs_prefix)
            if filename[:len(self.sdfs_prefix)] == self.sdfs_prefix:
                worker = self.workers[tid_counter % self.num_workers]
                task = Task(TaskType.Juice, self.mj_exe, tid_counter, self.sdfs_prefix, worker)
                task.data = filename
                self.tasks.append(task)
                tid_counter += 1


