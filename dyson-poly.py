#!/usr/bin/env python3

import polyinterface
import sys
from libpurecoollink.dyson import DysonAccount
from libpurecoollink.const import DYSON_PURE_COOL, DYSON_PURE_COOL_DESKTOP, FanPower, AutoMode, OscillationV2, FanSpeed, FrontalDirection, NightMode
from libpurecoollink.dyson_pure_state_v2 import DysonPureCoolV2State, DysonEnvironmentalSensorV2State

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'Dyson Controller'
        self.address = 'dysonctrl'
        self.primary = self.address
        self.dyson = None

    def start(self):
        # LOGGER.setLevel(logging.INFO)
        LOGGER.info('Started Dyson controller')
        if 'username' not in self.polyConfig['customParams'] or 'password' not in self.polyConfig['customParams']:
            LOGGER.error('Please specify username and password in the NodeServer configuration parameters');
            return False
        username = self.polyConfig['customParams']['username']
        password = self.polyConfig['customParams']['password']
        if 'country' in self.polyConfig['customParams']:
            country = self.polyConfig['customParams']['country']
        else:
            country = 'US'

        try:
            self.dyson = DysonAccount(username, password, country)
        except Exception as ex:
            LOGGER.error('ERROR connecting to the Dyson API: {}'.format(ex))
            return
        logged_in = self.dyson.login()
        if not logged_in:
            LOGGER.error('Failed to login to Dyson account')
        else:
            self.discover()

    def stop(self):
        LOGGER.info('Dyson is stopping')
        for node in self.nodes:
            if self.nodes[node].address != self.address:
                self.nodes[node].stop()

    def updateInfo(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, command=None):
        for dev in self.dyson.devices():
            address = dev.serial.replace('-','').lower()[:14]
            name = dev.name
            if not address in self.nodes:
                if dev.product_type == DYSON_PURE_COOL or dev.product_type == DYSON_PURE_COOL_DESKTOP:
                    LOGGER.info('Adding product: {}, name: {}'.format(dev.product_type, dev.name))
                    self.addNode(DysonPureFan(self, self.address, address, name, dev))
                else:
                    LOGGER.info('Found product type: {}, name: {} but it\'s not yet supported'.format(dev.product_type, dev.name))

    id = 'DYSONCTRL'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2}]


class DysonPureFan(polyinterface.Node):
    def __init__(self, controller, primary, address, name, device):
        super().__init__(controller, primary, address, name)
        self.device = device

    def start(self):
        LOGGER.info('Starting {}'.format(self.device.name))
        self.device.auto_connect()
        self.updateInfo()
        self.device.add_message_listener(self.on_message)

    def on_message(self, msg):
        if isinstance(msg, DysonPureCoolV2State):
            LOGGER.debug('Received State message for {}'.format(self.device.name))
            if msg.fan_power == FanPower.POWER_ON.value:
                if msg.auto_mode == AutoMode.AUTO_ON.value:
                    self.setDriver('ST', 11)
                else:
                    self.setDriver('ST', int(msg.speed))
            else:
                self.setDriver('ST', 0)
            if msg.oscillation == OscillationV2.OSCILLATION_ON.value:
                self.setDriver('GV4', 1)
            else:
                self.setDriver('GV4', 0)
            if msg.front_direction == FrontalDirection.FRONTAL_ON.value:
                self.setDriver('AIRFLOW', 0)
            else:
                self.setDriver('AIRFLOW', 1)
            if msg.night_mode == 'ON':
                self.setDriver('GV5', 1)
            else:
                 self.setDriver('GV5', 0)
            self.setDriver('GV6', int(msg.oscillation_angle_low))
            self.setDriver('GV7', int(msg.oscillation_angle_high))
            self.setDriver('GV8', int(msg.carbon_filter_state))
            self.setDriver('GV9', int(msg.hepa_filter_state))
        elif isinstance(msg, DysonEnvironmentalSensorV2State):
            LOGGER.debug('Received Environmental State message for {}'.format(self.device.name))
            temp = float(msg.temperature)
            tempC = round(temp - 273.15, 2)
            tempF = round(temp * 9 / 5 - 459.67, 2)
            self.setDriver('CLITEMP', tempC)
            self.setDriver('GV0', tempF)
            self.setDriver('CLIHUM', int(msg.humidity))
            self.setDriver('GV1', int(msg.particulate_matter_25))
            self.setDriver('GV2', int(msg.particulate_matter_10))
            self.setDriver('VOCLVL', int(msg.volatile_organic_compounds))
            self.setDriver('GV3', int(msg.nitrogen_dioxide))
            self.setDriver('GV10', int(msg.sleep_timer))
        else:
            LOGGER.warning('Unknown message received for {}'.format(self.device.name))
        LOGGER.debug('Received message {}'.format(str(msg)))

    def stop(self):
        LOGGER.info('Stopping {}'.format(self.device.name))
        self.device.disconnect()

    def updateInfo(self):
        LOGGER.debug(self.device.state)
        LOGGER.debug(self.device.environmental_state)
        if self.device.state.fan_power == FanPower.POWER_ON.value:
            if self.device.state.auto_mode == AutoMode.AUTO_ON.value:
                self.setDriver('ST', 11)
            else:
                self.setDriver('ST', int(self.device.state.speed))
        else:
            self.setDriver('ST', 0)
        temp = float(self.device.environmental_state.temperature)
        tempC = round(temp - 273.15, 2)
        tempF = round(temp * 9 / 5 - 459.67, 2)
        self.setDriver('CLITEMP', tempC)
        self.setDriver('GV0', tempF)
        self.setDriver('CLIHUM', int(self.device.environmental_state.humidity))
        self.setDriver('GV1', int(self.device.environmental_state.particulate_matter_25))
        self.setDriver('GV2', int(self.device.environmental_state.particulate_matter_10))
        self.setDriver('VOCLVL', int(self.device.environmental_state.volatile_organic_compounds))
        self.setDriver('GV3', int(self.device.environmental_state.nitrogen_dioxide))
        if self.device.state.oscillation == OscillationV2.OSCILLATION_ON.value:
            self.setDriver('GV4', 1)
        else:
            self.setDriver('GV4', 0)
        if self.device.state.front_direction == FrontalDirection.FRONTAL_ON.value:
            self.setDriver('AIRFLOW', 0)
        else:
            self.setDriver('AIRFLOW', 1)
        if self.device.state.night_mode == 'ON':
            self.setDriver('GV5', 1)
        else:
            self.setDriver('GV5', 0)
        self.setDriver('GV6', int(self.device.state.oscillation_angle_low))
        self.setDriver('GV7', int(self.device.state.oscillation_angle_high))
        self.setDriver('GV8', int(self.device.state.carbon_filter_state))
        self.setDriver('GV9', int(self.device.state.hepa_filter_state))
        self.setDriver('GV10', int(self.device.environmental_state.sleep_timer))

    def query(self):
        self.reportDrivers()

    def set_on(self, command):
        self.device.turn_on()

    def set_off(self, command):
        self.device.turn_off()

    def set_speed(self, command):
        speed = int(command.get('value'))
        if speed < 0 or speed > 11:
            LOGGER.error('Invalid speed selection {}'.format(speed))
        elif speed == 0:
            self.device.turn_off()
        elif speed == 11:
            self.device.enable_auto_mode()
        else:
            self.device.set_fan_speed(FanSpeed("%04d" % speed))

    def set_off_timer(self, command):
        timer = int(command.get('value'))
        if timer == 0:
            self.device.disable_sleep_timer()
        else:
            try:
                self.device.enable_sleep_timer(timer)
            except Exception as ex:
                LOGGER.error('Invalid timer value: {}'.format(ex))

    def set_auto(self, command):
        self.device.enable_auto_mode()

    def set_oscillation(self, command):
        osc = int(command.get('value'))
        if osc == 0:
            self.device.disable_oscillation()
        elif osc == 45:
            self.device.enable_oscillation(157, 202)
        elif osc == 90:
            self.device.enable_oscillation(135, 225)
        elif osc == 180:
            self.device.enable_oscillation(90, 270)
        elif osc == 350:
            self.device.enable_oscillation(5, 355)
        else:
            LOGGER.error('Invalid oscillation angle')

    def set_osc_angle(self, command):
        query = command.get('query')
        oscstart = int(query.get('L.uom14'))
        oscstop = int(query.get('H.uom14'))
        try:
            self.device.enable_oscillation(oscstart, oscstop)
        except Exception as ex:
            LOGGER.error('Invalid oscillation angle selection: {}'.format(ex))

    def set_airflow_fwd(self, command):
        self.device.enable_frontal_direction()

    def set_airflow_rew(self, command):
        self.device.disable_frontal_direction()

    def set_night_off(self, command):
        self.device.disable_night_mode()

    def set_night_on(self, command):
        self.device.enable_night_mode()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25},
               {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
               {'driver': 'GV0', 'value': 0, 'uom': 17},
               {'driver': 'CLIHUM', 'value': 0, 'uom': 22},
               {'driver': 'GV1', 'value': 0, 'uom': 56},
               {'driver': 'GV2', 'value': 0, 'uom': 56},
               {'driver': 'VOCLVL', 'value': 0, 'uom': 56},
               {'driver': 'GV3', 'value': 0, 'uom': 56},
               {'driver': 'GV4', 'value': 0, 'uom': 2},
               {'driver': 'AIRFLOW', 'value': 0, 'uom': 25},
               {'driver': 'GV5', 'value': 0, 'uom': 2},
               {'driver': 'GV6', 'value': 0, 'uom': 14},
               {'driver': 'GV7', 'value': 0, 'uom': 14},
               {'driver': 'GV8', 'value': 0, 'uom': 51},
               {'driver': 'GV9', 'value': 0, 'uom': 51},
               {'driver': 'GV10', 'value': 0, 'uom': 45}
              ]

    id = 'DYPFAN'

    commands = {
            'QUERY': query, 'DON': set_on, 'DOF': set_off, 'SPEED': set_speed, 'OFFTMR': set_off_timer, 'AUTO': set_auto, 'ROTATE': set_oscillation,
            'ANGLE': set_osc_angle, 'AFFWD': set_airflow_fwd, 'AFREW': set_airflow_rew, 'NIGHTON': set_night_on, 'NIGHTOFF': set_night_off
               }


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Dyson')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
