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

def webapi_write_metrics(msg_obj,url,auth_bearer):

    headers = {
        "Authorization": "Bearer {auth_bearer}".format(auth_bearer=auth_bearer),
        'Content-Type': 'application/json'
    }

    print(msg_obj.export_message())
    result = requests.post(url, data=msg_obj.export_message(), headers=headers)
    if not result.ok:
        logging.error("Error while exporting data to graphite: {}".format(result.text))
    return result.ok

## local defaults
redis_server = "localhost"
redis_port = 6379
redis_list = "metrics_webapi"
redis_database = 0
env_logger_file = "{homedir}/webapi_exporter.log".format(homedir=os.path.expanduser("~"))

publish_error_counter = 0

## CLI parser
cli_parser = argparse.ArgumentParser(description='Script for exporting messages from redis queue to pubsub topic')
cli_parser.add_argument('--redis-port', action='store', type=int, required=False, default=redis_port,help="Redis port to connect too")
cli_parser.add_argument('--redis-server', action='store', type=str, required=False, default=redis_server,help="Redis server host address")
cli_parser.add_argument('--redis-list', action='append', type=str, required=False, default=redis_list,help="On which Redis list I should work")
cli_parser.add_argument('--redis-database', action='store', type=int, required=False, default=redis_database,help="On which Redis list I should work")
cli_parser.add_argument('--logger-file', action='store', type=str, required=False, default=env_logger_file,help="Debug messages to file")
cli_parser.add_argument('--url', action='store', type=str, required=True ,help="URL to push metrics")
cli_parser.add_argument('--auth', action='store', type=str, required=True ,help="AUTH bearer")

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
                    if msg_object.get_measure_name() == 'MSGC_TEMPERATURE':
                        try:
                            publishing_result = webapi_write_metrics(msg_object,url=cli_args.url,auth_bearer=cli_args.auth)
                            if not publishing_result:
                                publish_error_counter += 1
                        except Exception:
                            publish_error_counter += 1
                            logging.error("Error during message publishing")
                            traceback.print_exc()
                            logging.error(traceback.print_exc())
                            time.sleep(60*publish_error_counter)

                time.sleep(0.5)
            except Exception:
                traceback.print_exc()
                logging.error(traceback.print_exc())
        else:
            logging.info("Redis queue is empty. waiting")
            time.sleep(60)

        if publish_error_counter > 10:
            logging.fatal("Over 10 error related with message publishing. Exiting")
            sys.exit(-1)
