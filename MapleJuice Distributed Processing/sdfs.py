import time
import os
import json
import threading

from logger import Logger
from sdfs_namenode import NameNodeServer
from sdfs_datanode import DataNodeServer
from membership import MembershipServer
from message import MessageType

class SDFSServer:
    def __init__(self):
        self.membershipList = MembershipServer()
        self.nameNode = NameNodeServer(self.membershipList)
        self.dataNode = DataNodeServer()
        self.logger = Logger(name="SDFSServer").logger

    def listener(self):
        '''listen to command line inputs '''
        while True:
            arg = input('--> ')
            args = arg.split(' ')
            # Client PUT request: put `local_filename` `sdfs_filename`
            if args[0] == 'put' and len(args) == 3:
                local_filename = args[1]
                sdfs_filename = args[2]
                self.nameNode.handleClientRequest(MessageType.PUT, sdfs_filename, local_filename)
            # Client GET request: put `local_filename` `sdfs_filename`
            elif args[0] == 'get' and len(args) == 2:
                sdfs_filename = args[1]
                self.nameNode.handleClientRequest(MessageType.GET, sdfs_filename)

            elif args[0] == 'delete' and len(args) == 2:
                sdfs_filename = args[1]
                self.nameNode.handleClientRequest(MessageType.DELETE, sdfs_filename)

            elif args[0] == 'ls' and len(args) == 2:
                sdfs_filename = args[1]
                self.nameNode.print_file(sdfs_filename)

            elif arg == 'store':
                self.dataNode.print()
            elif arg == 'print':
                self.membershipList.print()
            elif arg == 'switch':
                self.membershipList.switch()
            elif arg == 'leave':
                self.membershipList.leave()
            elif arg == 'join':
                self.membershipList.join()
            else:
                print('[ERROR] Invalid input argument %s' % arg)

    def run(self):
        self.membershipList.run()
        self.nameNode.run()
        self.dataNode.run()
        # Begin listenting to command line inputs 
        self.listener()

if __name__ == '__main__':
    s = SDFSServer()
    s.run()
