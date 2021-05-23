# MP3: MapleJuice, a distributed processing framework (similar to MapReduce) which runs on our SDFS and processes in parallel on a cluster.

## Instructions to run on VMs:

1. SSH into VMs

2. Install scp & paramiko
`sudo pip3 install scp paramiko`

3. Clone the repo

4. *Store the VMs' password in 'credentials.py'*:

`echo 'PASSWORD = "<password>"' > credentials.py`

5. Remember the password

`git config --global credential.helper 'cache --timeout=86400'`

6. Run the program

`python3 sdfs.py`

7. Run a Maple phase

`maple <maple_exe> <num_maples> <sdfs_intermediate_filename_prefix> <sdfs_src_directory>`

8. Run a Juice phase

`juice <juice_exe> <num_juices> <sdfs_intermediate_filename_prefix> <sdfs_dest_filename> delete_input={0,1}`

`python3 maplejuice.py`
`git pull && clear && python3 maplejuice.py`
`maple maple1.py 5 Task1 maple10k.txt`
`juice juice1.py 5 Task1 Task1_result.txt`
`cat Task1_result.txt`
