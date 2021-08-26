#!/usr/bin/env python3

import sys
import argparse
import serial
import time
import os
import redis

from os.path import expanduser


def get_device_id(line):
    return line[0:2]

def get_measure_code(line):
    return line[2:3]

def get_measure_value(line):
    return line[3:line.find('|',0)]

def get_cycle_number(line):
    return line[line.find('|',0)+1:len(line)].strip()

def decode_msg(line):
        msg = dict()
        msg["timestamp"] = time.time()
        msg["source_msg"] = line
        msg['decoded'] = 1
        try:
                msg["device_id"] = get_device_id(line)
                msg["measure_code"] = get_measure_code(line)
                msg["measure_value"] = get_measure_value(line)
                msg["cycle_number"] = get_cycle_number(line)
                decoding_status=True
        except:
                decoding_status=False
        return (msg,decoding_status)

def redis_channel_open(host,port):
    redis = redis.Redis(host=host,port=port)
    return redis

def redis_channel_close(redis):
    redis.close()
    return True

def redis_write_message(msg,redis,redis_list):
    # redis.lpush(database, "{msg}".format(msg))
    return True


####
uart_speed = 460800
uart_port = '/dev/ttyAMA0'
redis_server = "localhost"
redis_port = 6379
redis_list = "metrics"
msg_logger_file = "{homedir}/radio_msg.log".format(homedir=expanduser("~"))

# CLI parser
cli_parser = argparse.ArgumentParser(description='Script for getting messages from RPI UART and putting them into redis database')

cli_parser.add_argument('--uart-speed', action='store', type=int, required=False, default=uart_speed,help="UART port speed")
cli_parser.add_argument('--uart-port', action='store', type=str, required=False, default=uart_port,help="UART port in OS")
cli_parser.add_argument('--redis-port', action='store', type=int, required=False, default=redis_port,help="Redis port to connect too")
cli_parser.add_argument('--redis-server', action='store', type=str, required=False, default=redis_server,help="Redis server host address")
cli_parser.add_argument('--redis-list', action='store', type=str, required=False, default=redis_list,help="On which Redis list I should work")
cli_parser.add_argument('--logger-file', action='store', type=str, required=False, default=msg_logger_file,help="Name of the file to store data (beside Redis)")

cli_args = cli_parser.parse_args()

if __name__ == '__main__':
    # create serial handler
    serial_proxy = serial.Serial(cli_args.uart_port, cli_args.uart_speed, timeout=1)
    serial_proxy.flush()

    # open redis communication
    redis = redis_channel_open(hots=cli_args.redis_server,port=cli_args.redis_port,database=cli_args.redis_database)

    radio_log = open(cli_args.msg_logger_file,'a')

    while True:
        if serial_proxy.in_waiting > 0:
            try:
                line = serial_proxy.readline().decode('ascii').strip()
                print("RAW MSG received: {msg}".format(msg=line))
                if ('|' in line):
                    (msg_decoded,decoding_status) = decode_msg(line)
                    
                    if decoding_status == False:
                        print("ERR msg decoding erros")
                    print("MSG decoded: {msgd}".format(msgd=msg_decoded))
                    
                    redis_write_message(msg=msg_decoded,redis=redis,redis_list=cli_args.redis_list)

                    radio_log.write("{msgd}\n".format(msgd=msg_decoded))
                    
                    radio_log.flush()
            except:
                print("ERR handling message failed")

    radio_log.close()
    redis_close()