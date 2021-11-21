from google.cloud import bigquery
import base64, json, sys, os
import datetime
import traceback

env_bq_table_name = "iot_base_data"
env_bq_dataset = "iot_data"
env_debug = False

if 'ENV_BQ_TABLE' in os.environ:
    env_bq_table_name = os.environ['ENV_BQ_TABLE']
    
if 'ENV_BQ_DATASET' in os.environ:
    env_bq_dataset = os.environ['ENV_BQ_DATASET']

if 'ENV_DEBUG' in os.environ:
    env_debug = os.environ['ENV_DEBUG'] 
    

def debug_me(msg):
    if env_debug == 1:
        print(msg)

def prepare_data(event):
    dst_event = event
    if 'timestamp' in dst_event:
        msg_timestamp = dst_event.pop("timestamp")
        dst_event['event_timestamp'] = datetime.datetime.fromtimestamp(msg_timestamp)
    else:
        return "Unknown data", 417
    return dst_event

def insert_into_bigquery(event):
    try:
        bq_client = bigquery.Client()
        bq_client_dataset = bq_client.dataset(env_bq_dataset)
        bq_client_table = bq_client_dataset.table(env_bq_table_name)
        bq_destination_table = bq_client.get_table(bq_client_table)
        result = bq_client.insert_rows(bq_destination_table, [event])
        if result != []:
            debug_me(result)
    except Exception:
        print("Error while message inserting")
        debug_me(traceback.print_exc())
        return "insert error", 424

def pubsub_to_bigq(event, context):
    try:
        # get data from pubsub message
        pubsub_src_message = base64.b64decode(event['data']).decode('utf-8')
        debug_me("Source msg: {}".format(pubsub_src_message))
        # convert source data into BQ row format
        event_data = prepare_data(json.loads(pubsub_src_message))
    except Exception:
        print("Error while preparing message")
        debug_me(traceback.print_exc())
        return "Data error", 422
    # insert data into BigQuery
    insert_into_bigquery(event_data)
