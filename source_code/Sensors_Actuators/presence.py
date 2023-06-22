from MyMQTT import *
import time
import datetime
import json
import requests
from gpiozero import MotionSensor
import signal
import threading

import urllib.request
import requests
import threading
import json

import random


class MotionSensor:
    def __init__(self, pin):
        self.pin = pin
        self.motion_detected = False

    def is_motion_detected(self):
        return self.motion_detected

    def simulate_motion(self):
        self.motion_detected = True
        print(f"Motion detected by sensor {self.pin}")

    def simulate_no_motion(self):
        self.motion_detected = False
        print(f"No motion detected by sensor {self.pin}")


class PresenceSensor:
    def __init__(self, presence_info, service_catalog_info):
        # Retrieve broker info from service catalog
        self.service_catalog_info = json.load(open(service_catalog_info))
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' \
                         + self.service_catalog_info["ip_port_service"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["broker"]
        self.port = rjson["broker_port"]
        # Retrieve resource catalog info from service catalog
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' \
                         + self.service_catalog_info["ip_port_service"] + '/one_res_cat'
        r = requests.get(request_string)
        self.rc = json.loads(r.text)
        # Details about sensor
        self.presence_info = presence_info
        info = json.load(open(self.presence_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.pir = MotionSensor(27)

    def register(self):
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.presence_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def motion_callback(self):
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "motion",
                "u": "Boolean",
                "t": time.time(),
                "v": True
            }
        }
        self.client.myPublish(self.topic, msg)
        print("published\n" + json.dumps(msg))
        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()
    
    def simulate_random_motion(self):
        while True:
            for _ in range(5):  # Simulate 5 random motion events
                self.pir.simulate_motion()
                time.sleep(random.uniform(0.1, 0.5))  # Random delay between motion events
                self.pir.simulate_no_motion()
                self.motion_callback()
                time.sleep(random.uniform(0.1, 1.0))  # Random delay between no motion events
            time.sleep(60)  # Wait for a minute after 5 detections

if __name__ == '__main__':
    pres = PresenceSensor('presence_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=pres.background)
    f = threading.Thread(name='foreground', target=pres.foreground)
    r = threading.Thread(name='random_motion', target=pres.simulate_random_motion)

    b.start()
    f.start()
    r.start()

    try:
        #pres.motion_callback()
        while True:
            time.sleep(1)
        #pres.pir.when_motion = pres.motion_callback

        #pause()

    finally:
        pres.stop()
