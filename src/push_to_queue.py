#!/usr/bin/env python3

import argparse
import redis
import logging
import traceback
import sys,os
import datetime

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

####

redis_server = "localhost"
redis_port = 6379
redis_list = "metrics_pubsub"
redis_database = 0
msg_logger_debug = "{homedir}/json_loader.{dt}.log".format(homedir=os.path.expanduser("~"),dt=datetime.datetime.now().strftime('%Y%m%d_%H%M'))

# CLI parser
cli_parser = argparse.ArgumentParser(description='Script for getting messages from RPI UART and putting them into redis database')

cli_parser.add_argument('--redis-port', action='store', type=int, required=False, default=redis_port,help="Redis port to connect too")
cli_parser.add_argument('--redis-server', action='store', type=str, required=False, default=redis_server,help="Redis server host address")
cli_parser.add_argument('--redis-list', action='store', type=str, required=False, default=redis_list,help="On which Redis list I should work")
cli_parser.add_argument('--redis-database', action='store', type=int, required=False, default=redis_database,help="On which Redis list I should work")
cli_parser.add_argument('--json-file', action='store', type=str, required=True, help="File with JSONs to insert into Redis")
cli_parser.add_argument('--logger-debug',action='store', type=str, required=False, default=msg_logger_debug, help="File with internal debug and other logs")

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
    # open redis communication
    logging.info("Setting up Redis connection")
    redis_connection = redis_connection_open(host=cli_args.redis_server,port=cli_args.redis_port,database=cli_args.redis_database)

    with open(cli_args.json_file,"r") as input_json_msgs:
        for line in input_json_msgs:
            json_string = line.rstrip()
            try:
                msg = MessageObject()
                validation = msg.create_message_from_json(json_string)
                e=msg.get_validation_errors()
                if 'no measure name' in e:
                    msg.set_measure_name(msg.get_measure_name_by_code(msg.get_measure_code()))
                    validation = msg.validate()
                    logging.info('adding info about measure code')
                validation = msg.validate()
                if not validation:
                    logging.error("JSON not parsable; {js}".format(js=json_string))
                    logging.error("Errors: {e}".format(e=msg.get_validation_errors()))
                else:
                    msg_to_push = msg.export_message()
                    logging.info("Message to put {}".format(msg_to_push))

                    try:
                        push_stat = redis_write_message(msg_to_push, redis_connection, cli_args.redis_list)
                        if push_stat:
                            logging.info("Msg send into redis")
                    except Exception:
                        logging.error(traceback.print_exc())

            except Exception:
                logging.error(traceback.print_exc())


