import mlx90614
from time import sleep

# I2C pin configuration
SDA_PIN = 22  # SDA = data line
SCL_PIN = 21  # SCL = clock line

# Create an instance of the sensor
sensor = mlx90614.mlx90614(SCL=SCL_PIN, SDA=SDA_PIN)

# Set user-defined emissivity (e.g. human skin ~0.98)
USER_EMISSIVITY = 0.98
sensor.emissivity = USER_EMISSIVITY

# Hysteresis value in Kelvin – prevents printing minor fluctuations,
# which would clutter the terminal output
HYSTERESIS = 1.0
last_temp = None

while True:
    # Read object temperature in Kelvin
    # secure=True → perform PEC check (ensures data integrity)
    obj_temp_K = sensor.t_obj1(secure=True)

    # Print only if the change exceeds hysteresis
    if last_temp is None or abs(obj_temp_K - last_temp) > HYSTERESIS:
        last_temp = obj_temp_K

        # Convert to Celsius
        amb_temp_C = sensor.to_C(sensor.t_ambient(secure=True))
        obj_temp_C = sensor.to_C(obj_temp_K)
        corr_temp_C = sensor.to_C(sensor.correct_temperature())

        # Print results
        print(f"Ambient (sensor) temperature: {amb_temp_C:.2f} °C")
        print(f"Object temperature: {obj_temp_C:.2f} °C")
        print(f"Emissivity from sensor register: {sensor.reg_emissivity:.2f}")
        print(f"User-defined emissivity: {USER_EMISSIVITY:.2f}")
        print(f"Corrected object temperature: {corr_temp_C:.2f} °C")
        print("---")

    sleep(0.2)  # Delay to avoid too frequent readings
