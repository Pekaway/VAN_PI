
# Dimmy Version 1
**OBSOLET**

- 7 Channel Mosfet (6x3A + 1x10A)
- PCA9685 
- Wemos d1/Wemos Esp32 

# Dimmy Version 2 ([Shop](https://vanpi.de/products/van-pi-dimmy-pcb))

- 7 Channel Mosfet (6x3A + 1x10A)
- PCA9685 
- Wemos d1/Wemos Esp32 
- 4x onboard standard car fuses
- I2C support

## Software

### Wired (I2C)([Quickstart](/Quickstarts/Dimmy/ENG/VPI-DIM-PCB_ENG_WIRED.pdf)): 
Connect the Dimmy PCB to the VAN PI Relayboard via JST PH 4pin cable and it will work directly. (Using VAN PI OS) 

### Standalone ([Quickstart](/Quickstarts/Dimmy/ENG/VPI-DIM-PCB_ENG_Standalone.pdf)):
Control the 7 Channel via GPIO button/switches. 
- supports dimming by keeping pressed
- sleep timer (long pressing while active)
  
- S1 –> all
- S2 –> LED 1
- S3 –> LED 2
- S4 –> LED 3
- S5 –> LED 4
- S6 –> LED 5
- S7 –> LED 6
- S8 –> LED 7
 

 ### WiFi ([Quickstart](/Quickstarts/Dimmy/ENG/ENG_PekawayDIMMY_WIFI.pdf)): 
Connect the Dimmy via WiFi to the VAN PI. (Using VAN PI OS) 

### Pekaway Mota Wemos d1 (Esp8266/Esp32): 
Flash Pekaway Mota with our Onboard Flasher or with our Online Flasher. 
- Supports dimming via VAN PI OS (MQTT) 
- Supports reading DS18B20 via 3pin Connector
- Supports GPIO Readings -> in development
		- esp32 8xGPIO 
		- esp8266 4xGPIO

Firmware pekawayMOTA
We compiled a custom version of  [Tasmota.io](https://tasmota.github.io/docs), to add the support for the PCA9685 PWM Controller.
You can flash the firmware with the onboard flasher using the VanPi system or you can use our [Webinstaller](https://flashesp.pekaway.de). 




### Flashtool:

[Pekaway Online Flasher](https://flashesp.pekaway.de)

### [Video (DE)](https://www.youtube.com/watch?v=uSyl_5VbsuM)


## Known Issues
- Pullup resistors (R21-R29) prevent boot, there are removed on the PCB in [our shop](https://vanpi.de/products/van-pi-dimmy-pcb)
