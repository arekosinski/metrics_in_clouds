#!/usr/bin/env python3

import argparse
import serial
import time
import redis
import logging
import traceback
import threading
import queue
import sys,os
import json

sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/lib")

# import message_object
from message_object import MessageObject

def redis_connection_open(host,port,database):
    redis_conn = redis.Redis(host=host,port=port,db=database)
    return redis_conn

def redis_connection_close(redis):
    redis.close()
    return True

def redis_write_message(msg,redis_conn,redis_list):
    return redis_conn.lpush(redis_list, msg)

def validate_deviceid_drop_list(device_id,drop_list):
    if device_id in drop_list:
        return True
    return False

def write_message_to_storage(processing_queue,redis_lists):
    while True:
        msg = processing_queue.get()
        msg_received_count =+ 1

        logging.debug("Processing {sensor_id}:{measurment_id}:{cycle}" \
            .format(sensor_id=msg.get_device_id(),measurment_id=msg.get_measure_code(),cycle=msg.get_cycle_number())
        )

        if validate_deviceid_drop_list(msg.get_device_id(),msg_drop_by_deviceid):
            processing_queue.task_done()
            continue

        # writing to file
        try:
            radio_log.write("{msgd}\n".format(msgd=msg.export_message()))

            if msg_received_count % 100 == 0:
                logging.info("Messages processed: {msg_c}".format(msg_c=msg_received_count))
                radio_log.flush()

        except Exception:
            traceback.print_exc()
            logging.error(traceback.print_exc())

        # writing to redis
        for r_list in redis_lists:
            try:
                redis_writing_status = redis_write_message(msg=msg.export_message(),redis_conn=redis_connection,redis_list=r_list)
                if redis_writing_status == False:
                    logging.error("Problem with writing message to redis database")
            except Exception:
                traceback.print_exc()
                logging.error(traceback.print_exc())

        processing_queue.task_done()

####

redis_server = "localhost"
redis_port = 6379
redis_lists = ["metrics_pubsub","metrics_graphite","metrics_webapi"]
redis_database = 0
msg_logger_file = "{homedir}/radio_msg.log".format(homedir=os.path.expanduser("~"))
msg_logger_debug = "{homedir}/msg_uart_reader.log".format(homedir=os.path.expanduser("~"))
msg_received_count = 0
msg_drop_by_deviceid = ["99"]
uart_cfg_file = "{homedir}/uart_reader_cfg.json".format(homedir=os.path.expanduser("~"))

messages_queue = queue.Queue()

# CLI parser
cli_parser = argparse.ArgumentParser(description='Script for getting messages from RPI UART and putting them into redis database')

cli_parser.add_argument('--redis-port', action='store', type=int, required=False, default=redis_port,help="Redis port to connect too")
cli_parser.add_argument('--redis-server', action='store', type=str, required=False, default=redis_server,help="Redis server host address")
cli_parser.add_argument('--redis-list', action='append', type=str, required=False, default=redis_lists,help="On which Redis list I should work")
cli_parser.add_argument('--redis-database', action='store', type=int, required=False, default=redis_database,help="On which Redis list I should work")
cli_parser.add_argument('--logger-file', action='store', type=str, required=False, default=msg_logger_file,help="Name of the file to store data (beside Redis)")
cli_parser.add_argument('--logger-debug',action='store', type=str, required=False, default=msg_logger_debug, help="File with internal debug and other logs")
cli_parser.add_argument('--cfg-file', action='store', type=str, required=False, default=uart_cfg_file ,help="Graphite configuration in JSON file")

cli_args = cli_parser.parse_args()

logging.basicConfig(
    format='%(asctime)s %(levelname)s [%(threadName)10s]: %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(cli_args.logger_debug),
        logging.StreamHandler()
    ]   
)
logging.info("Setting up env")

if __name__ == '__main__':

    #uart_reader graphite configuratiob
    try:
        with open(cli_args.cfg_file,"r") as json_file:
            uart_configuration = json.load(json_file)
        logging.info("Uart reader configuration loaded")
    except Exception:
        logging.fatal("Cant load configuraion for uart")
        sys.exit(-1)

    # create serial handler        
    logging.info("Setting up serial connection")
    serial_proxy = serial.Serial(uart_configuration['uart_port'], uart_configuration['uart_speed'], timeout=1)
    serial_proxy.flush()

    # open redis communication
    logging.info("Setting up Redis connection")
    redis_connection = redis_connection_open(host=cli_args.redis_server,port=cli_args.redis_port,database=cli_args.redis_database)

    logging.info("Setting up local file for writing")
    radio_log = open(cli_args.logger_file,'a')

    logging.info("Setting up threads")
    thread_msg_writer = threading.Thread(name="msgWriter", target=write_message_to_storage, args=(messages_queue,cli_args.redis_list))
    thread_msg_writer.setDaemon(True)
    thread_msg_writer.start()

    logging.info("Reading messages from serial in loop")
    while True:
        if serial_proxy.in_waiting > 0:
            try:
                line = serial_proxy.readline().decode('ascii').strip()
                logging.info("RAW MSG received: {msg}".format(msg=line))

                if MessageObject.detect_version(line):
                    msg = MessageObject(line)
                    msg.set_location_id(uart_configuration['location_id'])

                    # put message to queue for further processing
                    if msg.validate() == True:
                        messages_queue.put(msg)
                        logging.debug("Message queued: {sensor_id}:{measurment_id}:{cycle}" \
                            .format(sensor_id=msg.get_device_id(),measurment_id=msg.get_measure_code(),cycle=msg.get_cycle_number())
                        )
                    else:
                        logging.warning("msg decoding erros")
                        logging.debug("Parsing errors: {err}".format(err = ",".join(msg.get_validation_errors())))

            except Exception:
                traceback.print_exc()
                logging.error(traceback.print_exc())

    messages_queue.join()
    redis_connection_close(redis_connection)
    radio_log.flush()
    radio_log.close()
    
