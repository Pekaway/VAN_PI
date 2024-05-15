import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(0, GPIO.OUT)
GPIO.output(0, GPIO.LOW)
