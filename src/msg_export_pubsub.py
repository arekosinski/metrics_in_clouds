#!/usr/bin/env python3

import sys
import argparse
import time
import os
import redis
import logging
import traceback
import json
from google.oauth2 import service_account

from google.cloud import pubsub_v1

sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/lib")

## functions
def redis_connection_open(host,port,database):
    redis_conn = redis.Redis(host=host,port=port,db=database)
    return redis_conn

def redis_connection_close(redis):
    redis.close()
    return True

def redis_write_message(msg,redis_conn,redis_list):
    return redis_conn.lpush(redis_list, msg)

## local defaults
env_gcp_topic_name = "iot-data"
env_gcp_project_name = "data-integration-playground"
env_gcp_auth_file = "{homedir}/data-integration-playground.json".format(homedir=os.path.expanduser("~"))
redis_server = "localhost"
redis_port = 6379
redis_list = "metrics_pubsub"
redis_database = 0
env_logger_file = "{homedir}/pubsub_exporter.log".format(homedir=os.path.expanduser("~"))

publish_error_counter = 0

## CLI parser
cli_parser = argparse.ArgumentParser(description='Script for exporting messages from redis queue to pubsub topic')

cli_parser.add_argument('--pubsub-topic', action='store', type=str, required=False, default=env_gcp_topic_name,help="GCP PubSub topic name")
cli_parser.add_argument('--gcp-project', action='store', type=str, required=False, default=env_gcp_project_name,help="GCP Project name")
cli_parser.add_argument('--gcp-auth-json', action='store', type=str, required=False, default=env_gcp_auth_file,help="GCP Project name")

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

    logging.info("Performing GCP Auth using {auth_file}".format(auth_file=cli_args.gcp_auth_json))
    service_account_info = json.load(open(cli_args.gcp_auth_json))
    
    credentials = service_account.Credentials.from_service_account_info(service_account_info)

    publisher = pubsub_v1.PublisherClient(credentials=credentials)

    pubsub_topic = publisher.topic_path(cli_args.gcp_project, cli_args.pubsub_topic)

    redis_list_length = redis_connection.llen(cli_args.redis_list)
    logging.info("Statup: Redis queue length to process: {llen}".format(llen=redis_list_length))

    while True:

        redis_list_length = redis_connection.llen(cli_args.redis_list)
        if redis_list_length % 10 == 0:
            logging.info("Redis queue length to process: {llen}".format(llen=redis_list_length))

        if redis_list_length > 0:
            try:
                rmsg = redis_connection.lpop(cli_args.redis_list)

                try:
                    publishing_result = publisher.publish(pubsub_topic, rmsg)
                    
                except Exception:
                    publish_error_counter += 1
                    logging.error("Error during message publishing")
                    traceback.print_exc()
                    logging.error(traceback.print_exc())
                    time.sleep(60*publish_error_counter)
                    
                time.sleep(0.05)
            except Exception:
                traceback.print_exc()
                logging.error(traceback.print_exc())    
        else:
            logging.info("Redis queue is empty. waiting")
            time.sleep(60)

        if publish_error_counter > 10:
            logging.fatal("Over 10 error related with message publishing. Exiting")
            sys.exit(-1)
        
