from machine import Pin, I2C
from micropython import const


# mlx90614 datasheet na https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf

ADDR = const(0x5A)  # Výchozí I2C adresa MLX90614
FREQ = const(100_000)  # frekvence komunikace

# registry
RAW_IR1 = const(0x04)
TA = const(0x06)
TO1 = const(0x07)
EMISSIVITY = const(0x24)

# Piny
SDA = const(21)
SCL = const(22)

# Inicializace I2C
i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)

# Pomocná funkce pro čtení 16bitového registru
def read16(reg) -> int:
    i2c.writeto(ADDR, bytes([reg]))
    ADDRW = ADDR << 1 | 0 # Dle specifikace posun 7bit adresy o bit vlevo plus 0 nakonec je zápis
    AADRR = ADDR << 1 | 1 # Dle specifikace posun 7bit adresy o bit vlevo plus 1 nakonec je čtení
    data = i2c.readfrom(ADDR, 3) # Přečte výsledek včetně PEC byte
    to_test = [ADDRW, reg, AADRR, data[0], data[1]] # složíme pole pro kontrolu součtu
    if (res_pec(to_test) == data[2]): # Otestujeme jestli vychází kontrolní součty
        print("Něco na senzoru zlobí")
        return 0
    return data[0] | (data[1] << 8)

# Pomocná fce na výpočet PEC(Packet Error Code) dle CRC-8 standardu
def res_pec(data_bytes):
    POLYNOM = const(0x07)
    pec = 0x00  # začíná se s nulou
    for byte in data_bytes:
        pec ^= byte # první XOR
        for _ in range(8):  # BYTE má 8 BITů
            if pec & 0x80:
                pec = (pec << 1) ^ POLYNOM  # XOR s polynomem
            else:
                pec <<= 1
            pec &= 0xFF
    return pec


# *********************** Testování *****************

# Čtení potřebných registrů
ir_raw = read16(RAW_IR1)
t_amb_raw = read16(TA)
t_obj_raw = read16(TO1)
eps_raw = read16(EMISSIVITY)

# Převody
t_amb = t_amb_raw * 0.02  # K
t_obj = t_obj_raw * 0.02  # K
eps = eps_raw / 65535.0   # 0.0–1.0

# Výpočet konstanty k
delta_T = t_obj - t_amb
if delta_T == 0 or eps == 0:
    print("Nelze spočítat k – dělení nulou.")
else:
    k = ir_raw / (24 * eps * delta_T)
    print("=== Výsledky ===")
    print("IR raw       =", ir_raw)
    print("Tamb (K)     = {:.2f}".format(t_amb))
    print("Tobj (K)     = {:.2f}".format(t_obj))
    print("Emisivita ε  = {:.4f}".format(eps))
    print("Spočtená konstanta k = {:.4f}".format(k))
