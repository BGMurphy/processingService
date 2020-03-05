import connexion
import yaml
import logging
from connexion import NoContent
import os
import logging.config
import json
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.elements import and_
import datetime
import requests
from flask_cors import CORS, cross_origin

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

#STORE_SURGERY_INFO_REQUEST_URL = "http://localhost:8090/report/book_surgery"
#STORE_XRAY_REPORT_REQUEST_URL = "http://localhost:8090/report/xRay"
HEADERS = {"content-type":"application/json"}

DB_ENGINE = 'mysql+pymysql://' + app_config['datastore']['user'] + ':' + app_config['datastore']['password'] + '@' + \
    app_config['datastore']['hostname'] + ':' + app_config['datastore']['port'] + '/' + app_config['datastore']['db']
#Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

def get_hospital_stats():
    """ Get surgery info from the data store """

    logger = logging.getLogger('basicLogger')
    logger.info("Request started")

    if os.path.exists(app_config['datastore']['filename']):
        with open(app_config['datastore']['filename'], 'r') as f:
            data = json.loads(f.read())
            data = data['stats']
            logger.debug(data)
            logger.info("Request completed")
            return data, 200

    else:
        print("File not found")
        return 404

        with open(app_config['datastore']['filename'], 'w') as outfile:
            json.dump(data, outfile)

    return NoContent, 201

def populate_stats():
    """ Periodically update stats """
    logger = logging.getLogger('basicLogger')
    logger.info("Start Periodic Processing")

    # logger.info(parsed_json)

    now = datetime.datetime.now()
    current_time = now.strftime("%Y-%m-%dT%H:%M:%S")

    if os.path.exists(app_config['datastore']['filename']):
        with open(app_config['datastore']['filename'], 'r') as f:
            data = json.loads(f.read())

    else:
        data = {}
        data['stats'] = []
        data['stats'].append({
            'numXrays': 0,
            'numSurgeries': 0,
            'timestamp': "2010-01-23T11:50:40"
        })
        with open(app_config['datastore']['filename'], 'w') as f:
            f.write(json.dumps(data))

    numXrays = data['stats'][0]["numXrays"]
    numSurgeries = data['stats'][0]["numSurgeries"]

    params = {
        "startDate": data['stats'][0]['timestamp'],
        "endDate": current_time
      }

    surgeryResponse = requests.get(STORE_SURGERY_INFO_REQUEST_URL, params=params)
    xrayResponse = requests.get(STORE_XRAY_REPORT_REQUEST_URL, params=params)

    if(surgeryResponse.status_code == 200 and xrayResponse.status_code == 200):
        logger.info("Events recieved - surgeries: %s" % len(surgeryResponse.json()))
        logger.info("Events recieved - xRays: %s" % len(xrayResponse.json()))

        numXrays += len(xrayResponse.json())
        numSurgeries += len(surgeryResponse.json())

        newData = {}
        newData['stats'] = []
        newData['stats'].append({
            'numXrays': numXrays,
            'numSurgeries': numSurgeries,
            'timestamp': current_time
        })

        logger.debug(newData)
        with open(app_config['datastore']['filename'], 'w') as f:
            f.write(json.dumps(newData))
        logger.debug("Period processing has ended")

    else:
        logger.error("200 status code not recieved")



def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval',
                  seconds=app_config['scheduler']['period_sec'])
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml")
CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

if __name__ == "__main__":
# run our standalone gevent server
    init_scheduler()
    app.run(port=8100, use_reloader=False)