#!/usr/bin/env python3
'''
Simple prometheus exporter for the LYWSD03MMC thermometers using the 
custom firmware from https://github.com/atc1441/ATC_MiThermometer   
'''

from bluepy.btle import Scanner, DefaultDelegate
from prometheus_client import Gauge, start_http_server
import yaml
import argparse

# prometheus metrics
atc_temperature     = Gauge('atc_temperature', 'Temperature', ['mac', 'description']) 
atc_humidity        = Gauge('atc_humidity', 'Humidity', ['mac', 'description'])
atc_battery_level   = Gauge('atc_battery_level', 'Battery level in percentage.', ['mac', 'description'])
atc_battery_voltage = Gauge('atc_battery_voltage', 'Battery voltage in millivolts.', ['mac', 'description']) 
atc_signal_level    = Gauge('atc_signal_level', 'RSSI', ['mac', 'description'])


def ParseATCMessage(msg, macs):
    '''
    UID mac temperature humidity battery(%) battery(voltage) counter 
    msg argument contains hex string with raw announcement.
    macs argument contains dict with mapping between mac and description.
    e.g 1a18 a4:c1:38:36:d5:cf 0075 42 53 0b8e 17
    '''
    parsed = {
      "mac": msg[4:16],
      "temperature": int(msg[16:20],16) / 10,
      "humidity": int(msg[20:22],16),
      "battery_level": int(msg[22:24],16),
      "battery_voltage": int(msg[24:28],16),
      "counter": int(msg[29:31],16)
    }

    if parsed['mac'] in macs:
        parsed['description'] = macs[parsed['mac']]
    else:
        parsed['description'] = ''

    return parsed


def LoadMacsFile(file):
    '''
    Load yaml with a list of macs and human readable strings.
    aabbccddeef0: kitchen
    aabbccddeef1: porch
    '''
    try:
        with open(file) as f:
            data = yaml.load(f)
            return data
    except:
        return {}


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)



if __name__ == '__main__':
    # argument parsing
    parser = argparse.ArgumentParser(description='Prometheus exporter for github.com/atc1441/ATC_MiThermometer')
    parser.add_argument('--port', type=int, default=8000, help='Listen port')
    parser.add_argument('--macs', default='macs.yaml', help='File with macs and human readable descriptions')
    args = parser.parse_args()

    start_http_server(args.port)
    scanner = Scanner().withDelegate(ScanDelegate())

    macs = LoadMacsFile(args.macs)
    while True:
      devices = scanner.scan(10, passive=True)
      for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if value[:4] == '1a18':
                r = ParseATCMessage(value, macs)
                atc_temperature.labels(mac=r['mac'], description=r['description']).set(r['temperature'])
                atc_humidity.labels(mac=r['mac'], description=r['description']).set(r['humidity'])
                atc_battery_level.labels(mac=r['mac'], description=r['description']).set(r['battery_level'])
                atc_battery_voltage.labels(mac=r['mac'], description=r['description']).set(r['battery_voltage'])
                atc_signal_level.labels(mac=r['mac'], description=r['description']).set(dev.rssi)
