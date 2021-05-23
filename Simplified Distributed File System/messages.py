import json
import logging
from enum import Enum
from typing import Optional, Dict


class MessageType(Enum):
    JOIN = "JOIN"
    JOIN_RES = "JOIN_RES"
    LEAVE = "LEAVE"
    HEARTBEAT = "HEARTBEAT"
    REPORT = "REPORT"
    PUT = "PUT"
    PUT_RES = "PUT_RES"
    PUT_SUCCESS = "PUT_SUCCESS"
    GET = "GET"
    GET_RES = "GET_RES"
    GET_SUCCESS = "GET_SUCCESS"
    REPLICATE = "REPLICATE"
    DELETE =  "DELETE"              
    DELETE_REQ = "DELETE_REQ"
    LS = "LS"                       
    LS_RES = "LS_RES" 


required_fields_for_type = {
    MessageType.JOIN: ["sender_id", "sender_host", "sender_port"],
    MessageType.LEAVE: ["sender_id"],
    MessageType.HEARTBEAT: ["sender_id", "seqnum", "sender_host", "sender_port"],
    MessageType.REPORT: ["sender_id", "report_num", "sender_host", "sender_port", "file_list"],
    MessageType.JOIN_RES: ["mem_list"],
    MessageType.PUT: ["sender_id", "sender_host", "sender_port", "sdfs_fname"],
    MessageType.PUT_RES: ["target_hosts", "target_ports", "response_status"],
    MessageType.PUT_SUCCESS: ["sender_id", "sdfs_fname"],
    MessageType.GET: ["sender_id", "sender_host", "sender_port", "sdfs_fname"],
    MessageType.GET_RES: ["target_hosts", "target_ports", "response_status"],
    MessageType.GET_SUCCESS: ["sender_id", "sdfs_fname"],
    MessageType.REPLICATE: ["target_hosts", "target_ports", "sdfs_fname"],
    MessageType.DELETE: ["sender_id", "sdfs_file_name"], 
    MessageType.DELETE_REQ: ["sdfs_file_name"],
    MessageType.LS: ["sender_id", "sdfs_fname"],
    MessageType.LS_RES: ["sdfs_fname", "ls_result"]
}


def create_message(msg_type: MessageType, **kwargs) -> bytes:
    """
    Create data based on message type and provided content. Refer to
    `required_fields_for_type` for what parameters to pass in.
    :param id: node identifier
    :param seqnum: integer sequence number
    :param mem_list: MembershipList
    :param sender_host: hostname of sender node
    :param sender_port: port of sender node
    :param file_list: list of all files at sender node
    :return: A bytes representation of json message 
    """
    content = {}
    for is_type, required_fields in required_fields_for_type.items():
        if msg_type == is_type:
            for field in required_fields:
                if field not in kwargs:
                    raise ValueError(
                        f"Cannot find required parameter '{field}' when creating message of type '{msg_type.value}'"
                    )
                if field == "mem_list":
                    content[field] = kwargs["mem_list"].to_dict()
                else:
                    content[field] = kwargs[field]
            break

    content["type"] = msg_type.value
    return json.dumps(content).encode()


def parse_and_validate_message(byte_data: bytes) -> Optional[Dict]:
    """
    Parse received byte data into json. Check if all required fields are present.
    :return: None if a required field is missing or failed to parse JSON. Otherwise the parsed dict.
    """
    str_data = byte_data.decode("utf-8")
    try:
        dict_data = json.loads(str_data)
    except ValueError:
        logging.warn(f"Failed to decode json: {str_data}")
        return None

    if "type" not in dict_data:
        logging.warn(f"Message does not contain 'type' field: {str_data}")
        return None

    try:
        msg_type = MessageType(dict_data["type"])
    except ValueError:
        logging.warn(f"Message has invalid type field: {str_data}")
        return None

    for is_type, required_fields in required_fields_for_type.items():
        if msg_type == is_type:
            for field in required_fields:
                if field not in dict_data:
                    logging.warn(
                        f"Message has type '{msg_type.value}' but does not have field '{field}': {str_data}"
                    )
                    return None
            break

    return dict_data
