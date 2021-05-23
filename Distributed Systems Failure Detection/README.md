#MP1: Heartbeat Failure Detection 

Working repo for CS 425: Distributed Systems (Fall 2020) MP1.

## Instructions

To use our program, run `python3 introducer.py` from the introducer machine ('fa20-cs425-g22-01.cs.illinois.edu') then run `join` for the introducer to join the group.

On any other nodes you want to join, run `python3 server.py` then `join` to join the group/get starting information.

## Commands

`join`: contact the introducer to join the group. It returns information about alive nodes & the current heartbeat mode.
`list`: list the membership list of the current node.
`leave`: gracefully leave the group
`id`: print the node ID (the hostname and initialization time)
`swtich`: switch the current heartbeat mode
`mode`: print the current heartbeating mode