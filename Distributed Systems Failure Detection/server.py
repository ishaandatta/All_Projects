import sys
import os

from threading import Thread
from node import Node, Mode

node = Node(role='server', mode = Mode.GOSSIP)

t1 = Thread(target=node.listener)
t2 = Thread(target=node.heartbeater)
t3 = Thread(target=node.commander)

t1.daemon = True
t2.daemon = True
t3.daemon = True

t1.start()
t2.start()
t3.start()

while True:
    pass
