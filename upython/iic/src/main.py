import mlx90614
from time import sleep

mydev = mlx90614.mlx90614(21, 22)

emissivity = 0.98
raw = 0
ir = 1

while True:
    ir = mydev.read24(0x04)
    if (raw != ir):
        raw = ir
        print(mydev.t_ambient_c(True))
        print(mydev.t_obj1_c(True))
        print(mydev.correct_temperature_c(emissivity))
        print("***")
    sleep(1)
