
# Dimmy Version 1
**OBSOLET**

- 7 Channel Mosfet (6x3A + 1x10A)
- PCA9685 
- Wemos d1/Wemos Esp32 

# Dimmy Version 2

- 7 Channel Mosfet (6x3A + 1x10A)
- PCA9685 
- Wemos d1/Wemos Esp32 
- 4x onboard standard car fuses
- I2C support

## Software

### Wired (I2C): 
Connect the Dimmy PCB to the VAN PI Relayboard via JST PH 4pin cable and it will work directly. (Using VAN PI OS) 

### Pekaway Mota Wemos d1 (Esp8266/Esp32): 
Flash Pekaway Mota with our Onboard Flasher or with our Online Flasher. 
- Supports dimming via VAN PI OS (MQTT) 
- Supports reading DS18B20 via 3pin Connector
- Supports GPIO Readings -> in development
		- esp32 8xGPIO 
		- esp8266 4xGPIO

Firmware pekawayMOTA
We compiled a custom version of  [Tasmota.io](https://tasmota.github.io/docs), to add the support for the PCA9685 PWM Controller.
You can flash the firmware with the onboard flasher using the VanPi system or you can use our Webinstaller. 

### Standalone:
Control the 7 Channel via GPIO button/switches. 
	- supports dimming by keeping pressed
	- sleep timer (long pressing while active)


### Flashtool:

[Pekaway Online Flasher](https://flashesp.pekaway.de)

## Known Issues
- Pullup resistors (R21-R29) prevent boot, there are removed on the PCB in our shop
