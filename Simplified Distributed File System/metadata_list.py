import re
import time
import copy
import threading
from enum import Enum

from utils import get_display_id, log_to_file, get_hostname, list_to_str, id_to_address, demo_print, debug_print
from typing import Iterator, Tuple


class FileStatus(Enum):
    IDLE = "IDLE"
    WRITING = "WRITING"
    READING = "READING"

class Row:
    def __init__(
        self, filename: str, ids: list, writers: list, readers: list, status
    ):
        """
        :param filename: sdfs_fname
        :param ids: ids of servers that have sdfs_fname
        :param writers: current writer ids
        :param readers: current reader ids
        :param status: file status
        """
        self.filename = filename
        self.ids = ids # list(id)
        self.last_request = 0
        self.filesize = 0
        self.writers = writers # list(id)
        self.readers = readers # list(id)
        self.status = status

    @staticmethod
    def from_dict(d) -> "Row":
        rv = Row(
            filename=d["filename"],
            ids=d["ids"].split(' '),
            writers=d["writers"].split(' '),
            readers=d["readers"].split(' '),
            status=FileStatus[d["status"]],
        )
        return rv

    def to_dict(self) -> dict:
        rv = copy.deepcopy(self.__dict__)
        rv["ids"] = list_to_str(self.ids)
        rv["writers"] = list_to_str(self.writers)
        rv["readers"] = list_to_str(self.readers)
        rv["status"] = self.status.value  # Turn status into a string (so it can be serialized)
        return rv

    def __repr__(self) -> str:
        return f"filename: {self.filename}, ids: {self.ids}, writers: {self.writers}, readers: {self.readers}, status: {self.status.value}"

class MetadataList:
    def __init__(self):
        self.files = {}
        self.lock = threading.Lock()

    # add a file to list
    def add_file(self, filename: str, id):
        """
        :param id: id of the node being added
        """
        if filename in self.files.keys():
            if id not in self.files[filename].ids:
                self.files[filename].ids.append(id)
        else:
            self.files[filename] = Row(filename, [id], [], [], FileStatus.IDLE)

        log_to_file(f"File {filename} added to metadata list")

    def clear(self):
        with self.lock:
            self.files.clear()

    def update_node_file_list(self, sender_id: str, node_file_list: list):
        for filename, row in self.files.items():
            # remove this node from files it doesn't have a replica of
            if filename not in node_file_list:
                row.ids = [id for id in row.ids if id != sender_id]

        for filename in node_file_list:
            self.add_file(filename, sender_id)

    # update the state of a file in the metadata list
    def update_state(
        self, filename: str, status: FileStatus, writer = [], reader = []
    ):
        """
        :param filename: name of file to update
        :param status: New status of <filename>, should be from the FileStatus enum
        :param writer: New list of writers of <filename>
        :param reader: New list of readers of <filename>.
        """
        with self.lock:
            self.files[filename].status = status
            self.files[filename].writer = writer
            self.files[filename].reader = reader

    # update the values in this metadata list using another metadata list dict
    def update_from_dict(self, other_metadata_list_dict: dict):
        """
        :param other_mem_list: Other metadata list to copy values over from
        """
        for id, row_dict in other_metadata_list_dict.items():
            with self.lock:
                self.files[id] = Row.from_dict(row_dict)

    def contains_file(self, filename: str) -> bool:
        with self.lock:
            return filename in self.files

    def to_dict(self) -> dict:
        with self.lock:
            result = {}
            for id, row in self.files.items():
                result[id] = row.to_dict()
            return result

    def __getitem__(self, idx) -> Row:
        with self.lock:
            return self.files[idx]

    def __repr__(self) -> str:
        with self.lock:
            ret = []
            for filename, row in self.files.items():
                # filename = get_display_id(filename)
                ret.append(f"{filename}: {{{row}}}")
            return "\n".join(ret)

    def __iter__(self) -> Iterator[Tuple[str, Row]]:
        with self.lock:
            dict_copy = copy.deepcopy(self.files)
        for id, row in dict_copy.items():
            yield id, row
