import re
import socket
from datetime import datetime

demo_time = True

def demo_print(*args, **kwargs):
    print(*args, **kwargs)

def debug_print(*args, **kwargs):
    if not demo_time:
        print(*args, **kwargs)

LOG_FILE_NAME = "distributed.log"

# e.g. fa20-cs425-g22-10.cs.illinois.edu:2000-15:00:00
def generate_id(host: str, port: int) -> str:
    now = datetime.now().strftime("%H:%M:%S")
    node_id = f"{host}:{port}-{now}"
    return node_id


def get_hostname() -> str:
    rv = socket.gethostname()
    # Super stupid fix to make testing on my PC work
    if rv == "pop-os" or rv.endswith(".local"):
        rv = "localhost"
    return rv

# returns the VM number from a node id (e.g. 01, ..., or 10)
def get_host_number_id(node_id) -> str:
    res = re.match(r"fa20-cs425-g\d\d-(\d+).cs.illinois.edu", node_id)
    if res:
        return f"{res.groups()[0]}"
    return node_id

# returns the VM number and timestamp identifier
def get_display_id(node_id) -> str:
    res = re.match(r"fa20-cs425-g\d\d-(\d+).cs.illinois.edu:(\d+)-(\d\d:\d\d:\d\d)", node_id)
    if res:
        id_num = res.groups()[0]
        port = res.groups()[1]
        timestamp = res.groups()[2]
        return f"{id_num}:{port} ({timestamp})"
    return node_id

# get the host & port # out of a node id
def id_to_address(node_id) -> (str, int):
    res = re.match(r"^((([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])):(\d+)-\d\d:\d\d:\d\d$", node_id)
    if res:
        host = res.groups()[0]
        port = int(res.groups()[-1])
        return (host, port)
    return None

def log_to_file(content):
    with open(LOG_FILE_NAME, "a+") as file:
        now = datetime.now().strftime("%c")
        file.write(f"{now}: {content}\n")

def list_to_str(l) -> str:
    if not l:
        return ""
    s = str(l[0])
    for i in l[1:]:
        s += " "
        s += str(i)
    return s
