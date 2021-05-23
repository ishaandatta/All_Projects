import time
import os
import json
import threading

from logger import Logger
from sdfs_namenode import NameNodeServer as SDFS_NameNodeServer
from sdfs_datanode import DataNodeServer as SDFS_DataNodeServer
from membership import MembershipServer
from message import MessageType

from maplejuice_namenode import NameNodeServer as maplejuice_NameNodeServer
from maplejuice_datanode import DataNodeServer as maplejuice_DataNodeServer

class MapleJuice:
    def __init__(self):
        self.membershipList = MembershipServer()
        self.sdfs_nameNode = SDFS_NameNodeServer(self.membershipList)
        self.sdfs_dataNode = SDFS_DataNodeServer()
        self.maplejuice_nameNode = maplejuice_NameNodeServer(self.membershipList, self.sdfs_nameNode)
        self.maplejuice_dataNode = maplejuice_DataNodeServer()
        self.logger = Logger(name="MapleJuicer").logger

    def listener(self):
        '''listen to command line inputs '''
        while True:
            arg = input('--> ')
            args = arg.split(' ')
            # Client PUT request: put `local_filename` `sdfs_filename`
            if args[0] == 'put' and len(args) == 3:
                local_filename = args[1]
                sdfs_filename = args[2]
                self.sdfs_nameNode.handleClientRequest(MessageType.PUT, sdfs_filename, local_filename)
            # Client GET request: put `local_filename` `sdfs_filename`
            elif args[0] == 'get' and len(args) == 2:
                sdfs_filename = args[1]
                self.sdfs_nameNode.handleClientRequest(MessageType.GET, sdfs_filename)

            elif args[0] == 'delete' and len(args) == 2:
                sdfs_filename = args[1]
                self.sdfs_nameNode.handleClientRequest(MessageType.DELETE, sdfs_filename)

            elif args[0] == 'ls' and len(args) == 2:
                sdfs_filename = args[1]
                self.sdfs_nameNode.print_file(sdfs_filename)

            elif arg == 'store':
                self.sdfs_dataNode.print()
            elif arg == 'print':
                self.membershipList.print()
            elif arg == 'switch':
                self.membershipList.switch()
            elif arg == 'leave':
                self.membershipList.leave()
            elif arg == 'join':
                self.membershipList.join()

            elif args[0] == 'maple' and len(args) == 5:
                mj_exe = args[1]
                num_workers = args[2]
                sdfs_prefix = args[3]
                sdfs_location = args[4]
                self.maplejuice_nameNode.handleClientRequest(MessageType.MAPLE, mj_exe, num_workers, sdfs_prefix, sdfs_location)
                pass

            elif args[0] == 'juice' and len(args) == 5:
                mj_exe = args[1]
                num_workers = args[2]
                sdfs_prefix = args[3]
                sdfs_location = args[4]
                # delete_input = args[5]
                self.maplejuice_nameNode.handleClientRequest(MessageType.JUICE, mj_exe, num_workers, sdfs_prefix, sdfs_location)
                pass
            
            else:
                print('[ERROR] Invalid input argument %s' % arg)

    def run(self):
        self.membershipList.run()
        self.sdfs_nameNode.run()
        self.sdfs_dataNode.run()
        self.maplejuice_nameNode.run()
        self.maplejuice_dataNode.run()
        # Begin listenting to command line inputs 
        self.listener()

if __name__ == '__main__':
    s = MapleJuice()
    s.run()
