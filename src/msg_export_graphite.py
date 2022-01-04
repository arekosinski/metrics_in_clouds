#!/usr/bin/env python3

import sys
import argparse
import time
import os
import redis
import logging
import traceback
import json
import requests

sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/lib")

# import message_object
from message_object import MessageObject

## functions
def redis_connection_open(host,port,database):
    redis_conn = redis.Redis(host=host,port=port,db=database)
    return redis_conn

def redis_connection_close(redis):
    redis.close()
    return True

def redis_write_message(msg,redis_conn,redis_list):
    return redis_conn.lpush(redis_list, msg)

def get_metric_object(metric,value,timestamp,interval=60):
    metric_object = dict()
    metric_object['name'] = metric
    metric_object['metric'] = metric
    metric_object['value'] = value
    metric_object['interval'] = interval
    # metric_object['unit'] = Null
    metric_object['time'] = int(timestamp)
    metric_object['mtype'] = "count"
    # graphite_data['tags'] = []
    return metric_object

def graphite_write_metrics(msg_obj,configuration):

    headers = {
        "Authorization": "Bearer {user}:{password}".format(user=configuration['user'],password=configuration['password'])
    }

    metric_key = "hiot.{device}.{metric_name}".format(device=msg_obj.get_device_id(),metric_name=msg_obj.get_measure_name())
    metric_key_cycle = "hiot.{device}.cycle_number".format(device=msg_obj.get_device_id())
    logging.debug("Metric: {metric_key}:{value}".format(metric_key=metric_key,value=msg_obj.get_measure_value()))

    graphite_measure_data = get_metric_object(metric_key,msg_obj.get_measure_value(),msg_obj.get_timestamp())
    graphite_cycle_number = get_metric_object(metric_key_cycle,msg_obj.get_cycle_number(),msg_obj.get_timestamp())

    result = requests.post(configuration['url'], json=[graphite_measure_data,graphite_cycle_number], headers=headers)
    if result.status_code != 200:
        logging.error("Error while exporting data to graphite: {}".format(result.text))
    return result.ok

## local defaults
redis_server = "localhost"
redis_port = 6379
redis_list = "metrics_graphite"
redis_database = 0
env_logger_file = "{homedir}/graphite_exporter.log".format(homedir=os.path.expanduser("~"))
graphite_cfg_file= "{homedir}/graphite_cfg.json".format(homedir=os.path.expanduser("~"))

publish_error_counter = 0

## CLI parser
cli_parser = argparse.ArgumentParser(description='Script for exporting messages from redis queue to pubsub topic')

cli_parser.add_argument('--graphite-cfg-file', action='store', type=str, required=False, default=graphite_cfg_file ,help="Graphite configuration in JSON file")

cli_parser.add_argument('--redis-port', action='store', type=int, required=False, default=redis_port,help="Redis port to connect too")
cli_parser.add_argument('--redis-server', action='store', type=str, required=False, default=redis_server,help="Redis server host address")
cli_parser.add_argument('--redis-list', action='append', type=str, required=False, default=redis_list,help="On which Redis list I should work")
cli_parser.add_argument('--redis-database', action='store', type=int, required=False, default=redis_database,help="On which Redis list I should work")
cli_parser.add_argument('--logger-file', action='store', type=str, required=False, default=env_logger_file,help="Debug messages to file")

cli_args = cli_parser.parse_args()

logging.basicConfig(format='%(asctime)s %(levelname)s [%(threadName)10s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', \
    level=logging.DEBUG, \
    filename =cli_args.logger_file \
)
logging.info("Setting up env")


## main code
if __name__ == '__main__':

    # open redis communication
    logging.info("Setting up Redis connection")
    redis_connection = redis_connection_open(host=cli_args.redis_server,port=cli_args.redis_port,database=cli_args.redis_database)

    #reading graphite configuratiob
    try:
        with open(cli_args.graphite_cfg_file,"r") as json_file:
            graphite_configuration = json.load(json_file)
        logging.info("Graphite configuration loaded")
    except Exception:
        logging.fatal("Cant load configuraion for graphite")
        sys.exit(-1)

    redis_list_length = redis_connection.llen(cli_args.redis_list)
    logging.info("Statup: Redis queue length to process: {llen}".format(llen=redis_list_length))

    while True:

        redis_list_length = redis_connection.llen(cli_args.redis_list)
        if redis_list_length % 10 == 0:
            logging.info("Redis queue length to process: {llen}".format(llen=redis_list_length))

        if redis_list_length > 0:
            try:
                rmsg = redis_connection.lpop(cli_args.redis_list)
                msg_object = MessageObject()
                msg_object.create_message_from_json(rmsg)
                if msg_object.validate():
                    try:
                        publishing_result = graphite_write_metrics(msg_object,configuration=graphite_configuration)
                        if not publishing_result:
                            publish_error_counter += 1
                    except Exception:
                        publish_error_counter += 1
                        logging.error("Error during message publishing")
                        traceback.print_exc()
                        logging.error(traceback.print_exc())
                        time.sleep(60*publish_error_counter)
                        
                time.sleep(1)
            except Exception:
                traceback.print_exc()
                logging.error(traceback.print_exc())    
        else:
            logging.info("Redis queue is empty. waiting")
            time.sleep(60)

        if publish_error_counter > 10:
            logging.fatal("Over 10 error related with message publishing. Exiting")
            sys.exit(-1)