from MyMQTT import *
import time
import datetime
import json
import requests
#from gpiozero import LED
#from gpiozero.pins.mock import MockFactory
#import Adafruit_DHT
import threading
import urllib.request

#MockFactory.pin_factory = None

class LED:
    def __init__(self, pin):
        self.pin = pin
        self.state = False

    def on(self):
        self.state = True
        print(f"Pin {self.pin} turned on")

    def off(self):
        self.state = False
        print(f"Pin {self.pin} turned off")

    def is_lit(self):
        return self.state

class LEDLights:
    def __init__(self, led_info, service_catalog_info):
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
        self.led_info = led_info
        info = json.load(open(self.led_info))
        self.topic = info["servicesDetails"][0]["topic"] # topic dedicated to led
        self.topic_zone = info["servicesDetails"][0]["topic_zone"] # topic common to all zone
        self.topic_temp = info["servicesDetails"][0]["topicP"]
        self.clientID = info["Name"]
        self.timer = info["timer"]  # Timer
        self.cycle = info["duty_cycle"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        self.car_led1 = LED(24)  # Car green light
        self.car_led2 = LED(22)  # Car red light
        self.ped_led1 = LED(23)  # Pedestrian green light
        self.ped_led2 = LED(18)  # Pedestrian red light
        # LED functioning control sensor
        #normally the led_ctrl is via Adafruit_DHT11 --> gives temperature and humidity according to sensor, just kept constant for simulation.
        self.led_ctrl = (30,45)
        self.led_hum = 40    #Adafruit_DHT.DHT11  # Temperature & humidity sensor
        self.led_ctrl_pin = 25

    def register(self):
        # Check temperature is under emergency threshold
        humidity, temperature = self.led_ctrl
        if humidity is not None and temperature is not None:
            self.publish(self.topic_temp)
            print(f'Temperature of the traffic light = {temperature}')
            if temperature > 80:
                # Overheated traffic light: malfunctioning detected
                data = json.load(open(self.led_info))
                data["status"] = "Malfunctioning"
                json.dump(data, open(self.led_info, "w"))
                print("Traffic light overheated, malfunctioning detected.")
            else:
                # Temperature under control: traffic light correctly functioning
                data = json.load(open(self.led_info))
                data["status"] = "OK"
                json.dump(data, open(self.led_info, "w"))
            # Send registration request to Resource Catalog
            request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
            try:
                r = requests.put(request_string, json.dumps(data, indent=4))
                print(f'Response: {r.text}')
            except:
                print("An error occurred during registration")
        else:
            print('LED functioning sensor failure. Check wiring.')

    def start(self):
        self.client.start()
        time.sleep(3)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_zone)

    def stop(self):
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f'Message received: {payload}\n Topic: {topic}')
        if topic == self.topic_zone:
            # payload["e"]["v"] == 'car'
            self.car_led1.on()
            self.car_led2.off()
            self.ped_led1.off()
            self.ped_led2.on()
            print('Start car protocol')
        elif topic == self.topic:
            # payload["e"]["v"] == 'pedestrian'
            self.car_led1.off()
            self.car_led2.on()
            self.ped_led1.on()
            self.ped_led2.off()
            print('Start pedestrian protocol')
        self.led_cycle()

    def led_cycle(self):
        # Start regular functioning cycle
        timer = self.timer
        while timer > 0:
            timer -= self.cycle
            time.sleep(self.cycle)
            if self.car_led1.is_lit:
                self.car_led1.off()
                self.car_led2.on()
                self.ped_led1.on()
                self.ped_led2.off()
            else:
                self.car_led1.on()
                self.car_led2.off()
                self.ped_led1.off()
                self.ped_led2.on()
        # Turn off lights for energy saving
        self.car_led1.off()
        self.car_led2.off()
        self.ped_led1.off()
        self.ped_led2.off()
        print('Lights turned off for energy saving')
        
    def publish(self,topic):
        temperature = self.led_ctrl[1]
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "temp",
                "u": "float",
                "t": time.time(),
                "v": temperature
                }
            }
        self.client.myPublish(self.topic_temp,msg)
    def background(self):
        while True:
            self.register()
            time.sleep(5)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    led = LEDLights('led_info.json', 'service_catalog_info.json')

    b = threading.Thread(name='background', target=led.background)
    f = threading.Thread(name='foreground', target=led.foreground)

    b.start()
    f.start()

    while True:
        time.sleep(1)

    # led.stop()
