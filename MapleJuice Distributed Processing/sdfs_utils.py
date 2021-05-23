import json
import random

class ErrorCode:
    Normal = "normal"
    FileNotFound = "file not found"
    FileNotReady = "file not ready"
    NotEnoughNodes = "not enough nodes"

class FileStatus:
    # fileStatus: pendingUpload, pendingReplication, ready, pendingDelete, deleted, pendingChange
    Ready = "ready"
    Deleted = "deleted"
    PendingUpload = "pending_upload"
    PendingReplication = "pending_replication"

DEBUG = True

class SDFSFile:
    def __init__(self, filename, local_filename):
        self.NUM_REPLICA = 4

        self.local_filename = local_filename
        self.filename = filename
        self.sdfsname = f'{filename}_v0'
        self.version = 0
        self.status = FileStatus.PendingUpload
        self.replicas = []
        self.assigned = []
    
    def delete(self):
        self.replicas = []
        self.assigned = []
        self.status = FileStatus.Deleted

    def update(self, local_filename):
        ''' Update file version (e.g. `file_v0` -> `file_v1`); Reset `self.assigned` and
        `self.replicas` to empty list, while returning the old list of `self.replicas`
        '''
        self.local_filename = local_filename
        self.version += 1
        self.sdfsname = f'{self.filename}_v{self.version}'
        self.replicas = []
        self.assigned = []
        self.status = FileStatus.PendingUpload

    def assign_replicas(self, active_vms):
        ''' Select some active vms as the assigned replica for this sdfs file such that the number
        of assigned replicas is exactly the the required number of self.NUM_REPLICA '''
        num_needed = self.NUM_REPLICA - len(self.assigned)
        active_vms = set(active_vms) - set(self.assigned)

        if DEBUG:
            print(f'[DEBUG-SDFSFile-assignRep] previous assigned: {self.assigned}')

        new_assigned = random.sample(active_vms, num_needed)
        self.assigned += new_assigned

        if DEBUG:
            print(f'[DEBUG-SDFSFile-assignRep] newly assigned: {new_assigned}')

        return new_assigned

    def dictify(self):
        dicts = {
            'status': self.status,
            'local_filename': self.local_filename,
            'filename': self.filename,
            'sdfsname': self.sdfsname,
            'replicas': self.replicas, 
            'assigned': self.assigned, 
            'version': self.version,
        }
        return dicts

    def print(self):
        dicts = self.dictify()
        for key, val in dicts.items():
            print(f'{key:<15}: {val}')