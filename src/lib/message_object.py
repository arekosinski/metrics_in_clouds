#!/usr/bin/env python3

import datetime
import ast
import traceback

class MessageObject:

    dict_measure_codes = {
        "MSGC_TEMPERATURE": 1,
        "MSGC_HUMIDITY": 2,
        "MSGC_BATTERY_VOLTAGE": 3,
        "MSGC_TEMP_SENSOR_ERROR": 4,
        "MSGC_ALL_MESSAGES_SUCCESS": 5,
        "MSGC_ALL_SENDING_TRIALS" : 6,
        "MSGC_AVG_CYCLE_LENGTH" : 7,
        "MSGC_DELIVERY_RATIO" : 8,
        "MSGC_RETRANSMISSIONS" : 9,
        "MSGC_ACCU_VOLTAGE" : 10, # 0xA
        "MSGC_ID_1" : 11, # 0xB
        "MSGC_ID_2" : 12, # 0xC
        "MSGC_ID_3" : 13, # 0xD
        "MSGC_ID_4" : 14, # 0xE
        "MSGC_STARTUP_CODE" : 15 # 0xF
    }

    measure_name = None
    measure_code = None
    measure_value = None
    device_id = None
    timestamp = None
    cycle_number = None
    version = None

    validation_errors = []

    def __init__(self,msg_raw_line=None):
        if msg_raw_line is not None:
            self.source = msg_raw_line
            self.create_message_from_raw_data(self.source)

    def create_message_from_dict(self,msg_dict):
        try:
            if 'version' in msg_dict:
                self.set_version(msg_dict["version"])
            else:
                self.set_version(1)
            
            if 'timestamp' in msg_dict:
                self.set_timestamp(msg_dict["timestamp"])
            else:
                self.set_timestamp()

            self.set_measure_value(msg_dict["measure_value"])
            self.set_measure_code(msg_dict["measure_code"])
            self.set_measure_name(self.get_measure_name_by_code(msg_dict["measure_code"]))
            self.set_cycle_number(msg_dict["cycle_number"])
            self.set_device_id(msg_dict["device_id"])
        except:
            pass
        
        return self.validate()

    def create_message_from_string(self,msg_str):
        msg = ast.literal_eval(msg_str)
        return self.create_message_from_dict(msg)
    
    def create_message_from_raw_data(self,msg_raw_line):
        try:
            self.set_version(self.detect_version(msg_raw_line))
            self.set_timestamp()
            self.set_device_id(self.extract_device_id(msg_raw_line))
            self.set_measure_code(self.extract_measure_code(msg_raw_line))
            self.set_measure_name(self.get_measure_name_by_code(self.get_measure_code()))
            self.set_measure_value(self.extract_measure_value(msg_raw_line))
            self.set_cycle_number(self.extract_cycle_number(msg_raw_line))
        except Exception:
            traceback.print_exc()
        
        return self.validate()

    def export_message(self):
        msg = dict()
        msg["timestamp"] = self.get_timestamp()
        msg["device_id"] = self.get_device_id()
        msg["measure_code"] = self.get_measure_code()
        msg["measure_value"] = self.get_measure_value()
        msg["measure_name"] = self.get_measure_name()
        msg["cycle_number"] = self.get_cycle_number()
        msg["version"] = self.get_version()
        return str(msg)

    def set_version(self,version):
        self.version = version
        return True

    def get_version(self):
        return self.version   

    @staticmethod
    def detect_version(msg_raw_line):
        if '|' in msg_raw_line:
            return 1
        elif '!' in msg_raw_line:
            return 2
        else:
            return False

    def validate(self):
        if self.get_timestamp() is None:
            self.validation_errors.append("no timestamp")
        
        if self.get_device_id() is None:
            self.validation_errors.append("no device id")

        if self.get_measure_name() is None:
            self.validation_errors.append("no measure name")

        if self.get_measure_value() is None:
            self.validation_errors.append("no measure value")

        if self.get_measure_code() is None:
            self.validation_errors.append("no measure code")

        if self.get_cycle_number() is None:
            self.validation_errors.append("no cycle_number")

        if self.get_version() is None:
            self.validation_errors.append("no version")

        if len(self.validation_errors) > 0:
            return False
        else:
            return True

    def get_validation_errors(self):
        return self.validation_errors

    def extract_device_id(self,msg_raw_line):
        return msg_raw_line[0:2]

    def set_device_id(self,device_id):
        self.device_id = device_id
        return True

    def get_device_id(self):
        return self.device_id

    def extract_measure_code(self,msg_raw_line):
        return msg_raw_line[2:3]

    def set_measure_code(self,measure_code):
        self.measure_code = measure_code
        return True
    
    def get_measure_code(self):
        return self.measure_code

    def get_measure_code_by_name(self,measure_name):
        try:
            return self.dict_measure_codes[measure_name]
        except:
            return None

    def get_measure_name_by_code(self,measure_code):
        try:
            return list(self.dict_measure_codes.keys())[list(self.dict_measure_codes.values()).index( int(measure_code,16) )]
        except:
            return None

    def set_measure_name(self,measure_name):
        self.measure_name = measure_name
        return True

    def get_measure_name(self):
        return self.measure_name

    def extract_measure_value(self,msg_raw_line):
        return msg_raw_line[3:msg_raw_line.find('|',0)]

    def set_measure_value(self,measure_value):
        self.measure_value = measure_value
        return True

    def get_measure_value(self):
        return self.measure_value

    def extract_cycle_number(self,msg_raw_line):
        return msg_raw_line[msg_raw_line.find('|',0)+1:len(msg_raw_line)].strip()

    def set_cycle_number(self,cycle_number):
        self.cycle_number = cycle_number
        return True

    def get_cycle_number(self):
        return self.cycle_number

    def get_timestamp(self):
        return self.timestamp

    def set_timestamp(self,timestamp=None):
        if timestamp == None:
            self.timestamp = datetime.datetime.now().timestamp()
        else:
            self.timestamp = timestamp
