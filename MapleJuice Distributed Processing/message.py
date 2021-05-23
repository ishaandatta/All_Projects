import json

class MessageType:
    # Membership messages
    ML = 'membership_list'
    SWITCH = 'mode_switch'
    ACK = 'acknowledge'
    JOIN = 'join'
    # SDFS Client messages
    PUT = 'put'
    GET = 'get'
    DELETE = 'delete'
    # SDFS DataNode messages
    FILE_TABLE = 'file_table_broadcast'
    UPL_ACK = 'file_uploaded'
    REP_ACK = 'file_replicated'
    
    UPL_REQ = 'upload_request'
    REP_REQ = 'replication_request'
    DEL_REQ = 'deletion_request'
    GET_REQ = 'get_request'
    # Mapreduce Client messages
    MAPLE = 'maple'
    JUICE = 'juice'
    # Mapreduce DataNode messages
    JOB = 'job'
    TASK = 'task'
    JOB_ACK = 'job_ack'
    TASK_ACK = 'task_ack'

class Message:
    def __init__(self, body, type=MessageType.ML):
        self.type = type
        self.body = body
    
    def prepare(self):
        return json.dumps({'type': self.type, 'body': self.body})