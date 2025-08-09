import mlx90614
from time import sleep

sda = 22
scl = 21
mydev = mlx90614.mlx90614(SCL=scl, SDA=sda)

emissivity = 0.98
raw = 0
ir = 1

while True:
    ir = mydev.read24(0x04)
    if (raw != ir):
        raw = ir
        print("teplota senzoru: ", mydev.to_C(mydev.t_ambient(True)))
        print("teplota objektu: ", mydev.to_C(mydev.t_obj1(True)))
        print("Emisivita: ", mydev.emissivity)
        print("teplota objektu při změně emisivity: ", mydev.to_C(mydev.correct_temperature(emissivity)))
        print("***")
    sleep(1)
