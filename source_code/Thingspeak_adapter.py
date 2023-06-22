from MyMQTT import *
import time
import json
import requests
import threading
import numpy as np

import urllib.request
import requests
import threading
import json


class Thingspeak:
    def __init__(self, Thingspeak_info, service_catalog_info):
        # Retrieve broker info from service catalog
        self.service_catalog_info = json.load(open(service_catalog_info))
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["broker"]
        self.port = rjson["broker_port"]
        # Retrieve resource catalog info from service catalog
        request_string = 'http://' + self.service_catalog_info["ip_address_service"] + ':' + self.service_catalog_info["ip_port_service"] + '/one_res_cat'
        r = requests.get(request_string)
        self.rc = json.loads(r.text)
        # Details about sensor
        self.info = Thingspeak_info
        info = json.load(open(self.info))
        for s in info["serviceDetails"]:
            if s["serviceType"]=='MQTT':
                self.topicS = s["topicS"] #topic to which it is subscribed
                self.topicTemp = s["topictemp"]
        self.clientID = info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        #initialization of pedestrian and cars detection
        self.button_events = []
        self.presence_events = []
        self.temp = 0
        self.last_posted_timestamp = 0

        # Thingspeak details
        self.base_url = info["Thingspeak"]["base_url"]
        self.key = info["Thingspeak"]["key"]
        self.url_read = info["Thingspeak"]["url_read"]

    
    def register(self):
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")
    
    # Method to START and SUBSCRIBE
    def start(self):
        self.client.start()
        time.sleep(3)  # Timer of 3 second (to deal with asynchronous)
        self.client.mySubscribe(self.topicS)
        self.client.mySubscribe(self.topicTemp)

    # Method to UNSUBSCRIBE and STOP
    def stop(self):
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()
    
    def notify(self,topic, payload):
        messageReceived = json.loads(payload)
        if messageReceived["e"]["n"] == "button":
            obj = "pedestrian"
            self.button_events.append(obj)
        elif messageReceived["e"]["n"] == "motion":
            obj = "car"
            self.presence_events.append(obj)
        elif messageReceived["e"]["n"] == "temp":
            obj = messageReceived["e"]["v"]
            self.temp = obj
    
    def thingspeak_post(self):
        current_time = time.time()
        elapsed_time = current_time - self.last_posted_timestamp
        if elapsed_time >= 15:
            amount_ped = len(self.button_events) #amount of detected pedestrians in the last 15 seconds
            amount_cars = len(self.presence_events) #amount of detected cars in the last 15 seconds
            temp = self.temp
            URl = self.base_url  #This is unchangeble
            KEY = self.key  #This is the write key API of your channels

    	    #field one corresponds to the first graph, field2 to the second ... 
            HEADER = '&field1={}&field2={}&field3={}'.format(amount_ped,amount_cars,temp)
            NEW_URL = URl+KEY+HEADER
            URL_read = self.url_read
            print('The detection of a cars and pedestrian of the latest 15 seconds is posted on Thingspeak link: \n' + URL_read)
            data = urllib.request.urlopen(NEW_URL)
            print(data)
            response = requests.post(NEW_URL)

            if response.status_code == 200: #Post was succesfull
                self.last_posted_timestamp = current_time #update time stamp
                #clear the detections of cars and pedestrians
                self.button_events.clear()
                self.presence_events.clear()
    
    def foreground(self):
        self.start()

        while True:
            self.thingspeak_post()
            time.sleep(1)
    
    def background(self):
        while True:
            self.register()
            time.sleep(10)

if __name__ == '__main__':
    think = Thingspeak('Thingspeak_adapter_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=think.background)
    f = threading.Thread(name='foreground', target=think.foreground)


    b.start()
    f.start()

    try:
        while True:
            time.sleep(1)
    
    finally:
        think.stop()

    
    

    