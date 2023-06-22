from MyMQTT import *
import time
import datetime
import json
import requests
#from gpiozero import Button
#from signal import pause
import threading
import urllib.request
import requests
import threading
import json

import random

class Button:
    def __init__(self, pin):
        self.pin = pin
        self.state = False

    def is_pressed(self):
        return self.state

    def simulate_press(self):
        self.state = True
        print(f"Button {self.pin} pressed")

    def simulate_release(self):
        self.state = False
        print(f"Button {self.pin} released")

class PedestrianButton:
    def __init__(self, button_info, service_catalog_info):
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
        self.button_info = button_info
        info = json.load(open(self.button_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.but = Button(17)

    def register(self):
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.button_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print('An error occurred during registration')

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def press_callback(self):
        # Callback function for button press
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "button",
                "u": "Boolean",
                "t": time.time(),
                "v": True
            }
        }
        self.but.simulate_press()
        self.client.myPublish(self.topic, msg)
        print("published\n" + json.dumps(msg))

    
    #Simulate that the button is pressed randomly once every minut
    def simulate_random_button_press(self):
        while True:
            for _ in range(2):
                self.but.simulate_press()
                time.sleep(random.uniform(0.1, 0.5))  # Random delay between motion events
                self.but.simulate_release()
                self.press_callback()
                time.sleep(random.uniform(0.1, 1.0))  # Random delay between no motion events
            time.sleep(60) 
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    button = PedestrianButton('button_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=button.background)
    f = threading.Thread(name='foreground', target=button.foreground)
    r = threading.Thread(name='random_press', target=button.simulate_random_button_press)


    b.start()
    f.start()
    r.start()

    try:
        while True:
            time.sleep(1)
        #pause()

    finally:
        button.stop()
