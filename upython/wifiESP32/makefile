PORT:=a0


new:
	mpr -d $(PORT) mkdir lib

clean:
	mpr -d $(PORT) rm --rf // *

run:
	mpr -d $(PORT) run src/main.py

mount:
	mpr -d $(PORT) mount .

upload:
	mpr -d $(PORT) put src/*.py /
	mpr -d $(PORT) put src/lib/*.py lib/

flashusb:
	esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20250415-v1.25.0.bin

eraseusb:
	esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 erase_flash

flashacm:
	esptool.py --chip esp32 --port /dev/ttyACM0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20250415-v1.25.0.bin

eraseacm:
	esptool.py --chip esp32 --port /dev/ttyACM0 --baud 460800 erase_flash
