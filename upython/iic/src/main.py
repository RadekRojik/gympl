import mlx90614
from time import sleep

sda = 22
scl = 21
mydev = mlx90614.mlx90614(SCL=scl, SDA=sda)

emissivity = 0.98
hysterese = 1
last = None

while True:
    tmp = mydev.t_obj1(True)  # Basic single-register read
    if last is None or abs(tmp - last) > hysterese:  # If the temperature change is outside hysteresis, reprocess
        last = tmp
        print("Sensor temperature: ", mydev.to_C(mydev.t_ambient(True)))
        print("Object temperature: ", mydev.to_C(tmp))
        print("Emissivity from register: ", mydev.emissivity)
        print("Own emissivity: ", emissivity)
        print("Last temperature: ", last)
        print("Object temperature (with modified emissivity): ", mydev.to_C(mydev.correct_temperature(emissivity)))
        print("***")
    sleep(0.2)
