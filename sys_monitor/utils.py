from subprocess import check_output
from functools import reduce, wraps
from addict import Dict
from os.path import join, isfile
from pathlib import Path
from typing import List, Tuple
from collections.abc import Callable
from requests import get
from operator import sub
from .constants import ROOT_DIR
from .decorators import wrap_exceptions
from time import sleep
from collections import namedtuple
import docker
import socket
import csv
import sys
import pickle

__all__ = ['subtract_dicts', 'merge_dict', 'filter_dict', 'join_url', 'send_data',
           'save_csv', 'format_name', 'get_containers', 'get_container_pid', 'try_connect', 'receive', 'send_to']

# Represents a pair for a container
Pair = namedtuple('Pair', ['container', 'name'])


def subtract_dicts(dict1: dict, dict2: dict) -> dict:
    """ Subtracts values from dict1 and dict2 """
    if len(dict1) != len(dict2):
        raise KeyError("Mapping key not found")
    values = map(lambda _dict: reduce(sub, _dict),
                 zip(dict2.values(), dict1.values()))
    return dict(zip(dict1.keys(), map(lambda n: round(n, 4), values)))


def merge_dict(*dicts: List[dict]) -> dict:
    """ Merges multiple dictionaries """
    assert dicts != None
    assert all(i for i in dicts if isinstance(i, dict)) == True
    ret = dict()
    for d in dicts:
        ret.update(d)
    return ret


def filter_dict(_dict: dict, *keys: List[object]) -> dict:
    """ Apply a simple filter over a given dictionary
        Usage:
            >>> filter_dict({'a': 1, 'b': 2, 'c':3}, 'a', 'c')
            >>> {'a': 1, 'c': 3}
    """
    filters = keys
    if isinstance(keys[0], list):
        filters = keys[0]
    return {k: v for k, v in _dict.items() if k in filters}


def join_url(url: str, *pages: List[str]) -> str:
    """ Joins pages in a given URL. 
        Usage:
            >>> join('https://github.com', 'hrchlhck', 'sys-monitor')
            >>> 'https://github.com/hrchlhck/sys-monitor'
    """
    for page in map(str, pages):
        url += "/" + page
    return url


def load_json(url: str) -> dict:
    """ Parses a JSON to a Python dictionary """
    try:
        return get(url).json()
    except Exception as e:
        print(e)


def send_data(socket: socket.socket, data: dict, source: str) -> None:
    """ 
    This function is responsible for sending data via network socket
    to a TCP Server inside of sys_monitor/collector.py.

    Args:
        data (dict): A dictionary containing your data
        source (str) From where you are sending the data
        socket (socket.socket) TCP socket
    """
    temp = pickle.dumps({"source": source, "data": data})
    socket.send(temp)


def save_csv(_dict: dict, name: str, dir_name="") -> None:
    """ 
    Saves a dict into a csv 

    Args:
        _dict (dict): The dictionary that will be written or appended in the file
        name (str): The name of the file
        dir_name (str): Subdirectory inside ROOT_DIR/data that the file will be saved

    Raises:
        ValueError 
            if `dir_name` type isn't string 
    """
    global ROOT_DIR

    filename = "%s.csv" % name

    if 'win' in sys.platform:
        output_dir = join(ROOT_DIR, "data")
    else:
        output_dir = ROOT_DIR

    if dir_name and not isinstance(dir_name, str):
        raise ValueError("Expected str instead of %s" % type(dir_name))
    elif dir_name and isinstance(dir_name, str):
        output_dir = join(output_dir, dir_name)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_dir = join(output_dir, filename)

    mode = "a"

    if not isfile(output_dir):
        mode = "w"

    with open(output_dir, mode=mode, newline="") as f:
        writer = csv.DictWriter(f, _dict.keys())

        if mode == "w":
            writer.writeheader()

        writer.writerow(_dict)


def format_name(name):
    return "%s" % name.split('-')[0]


def get_containers(client: docker.client.DockerClient, platform=sys.platform, namespace='', to_tuple=False) -> List[docker.client.ContainerCollection]:
    """ 
    Returns a list of containers. 
        By default and for my research purpose I'm using Kubernetes, so I'm avoiding containers that
        contains 'POD' (Assigned by Kuberenetes) and 'k8s-bigdata' (Namespace in Kubernetes that I've created) 
        in their name. Furthermore I assume that this filter is only applied when the platform is Linux-based, 
        because I've created a Kubernetes cluster only in Linux-based machines, otherwise, if the platform
        is Windows or MacOS, the function will return all containers that are running.

    Args:
        client (DockerClient): Object returned by docker.from_env()
        platform (str): By default, It uses sys.platform to get the current system platform
        namespace (str): Used to filter containers created by Kubernetes. If empty, it returns all containers
        to_tuple (bool): Return a list of namedtuples that represent a pair of container and container name 
    """
    containers = client.containers.list()
    def _filter(x): return 'POD' not in x.name and namespace in x.name

    if not to_tuple:
        return list(filter(_filter, containers))
    return list(map(lambda container: Pair(container, container.name), filter(_filter, containers)))


def get_container_pid(container):
    cmd = ['docker', 'inspect', '-f', '{{.State.Pid}}', container.id]
    return int(check_output(cmd))


def try_connect(addr: str, port: int, _socket: socket.socket, timeout: int) -> None:
    """ 
        Function to try connection of a socket to a server

        Args:
            addr (str): Address of the server
            port (int): It's port
            _socket (socket.socket): Socket object you want to connect to the server
            timeout (int): Connection attempts
    """
    for i in range(timeout):
        print("Attempt %d" % int(i + 1))
        try:
            return _socket.connect((addr, port))
        except Exception as e:
            print(e)
        sleep(1)
    print("Connection timed out after %s retries" % str(timeout))
    exit(0)


def receive(_socket: socket.socket, buffer_size=1024, encoding_type='utf8') -> str:
    """ 
    Wrapper function for receiving data from a socket. It also decodes it to utf8 by default.

    Args:
        _socket (socket): Socket that will be receiving data from;
        buffer_size (int): Size of the buffer used by socket.recv() method;
        encoding_type (str): Encoding type for decoding incoming data.
    """
    # UDP
    addr = None
    if _socket.type == 2:
        data, addr = _socket.recvfrom(buffer_size)
    else:
        data = _socket.recv(buffer_size)
    return pickle.loads(data, encoding=encoding_type), addr


@wrap_exceptions(KeyboardInterrupt)
def send_to(_socket: socket.socket, data: object, address=tuple()) -> None:
    # UDP
    if _socket.type == 2 and address:
        _socket.sendto(pickle.dumps(data), address)
    else:
        _socket.send(pickle.dumps(data))
