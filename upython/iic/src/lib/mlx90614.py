from machine import Pin, SoftI2C
from micropython import const


# mlx90614 datasheet na https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf

ADDR = const(0x5A)  # Výchozí I2C adresa MLX90614
FREQ = const(50_000)  # frekvence komunikace

# registry
R_RAW_IR1 = const(0x04)
R_TA = const(0x06)
R_TO1 = const(0x07)
R_EMISSIVITY = const(0x24)

# CRC-8 spec
POLYNOM = const(0x07)


class mlx90614:
    def __init__(self, SDA, SCL) -> None:
        # self.i2c = I2C
        self.SDA = SDA
        self.SCL = SCL
        # self.data = []
        self.LSB = 0
        self.MSB = 0
        self.PEC = 0
        self.ADDR_WRITE = (
            ADDR << 1 | 0
        )  # Dle specifikace posun 7bit adresy o bit vlevo plus 0 nakonec je zápis
        self.ADDR_READ = (
            ADDR << 1 | 1
        )  # Dle specifikace posun 7bit adresy o bit vlevo plus 1 nakonec je čtení
        self.device = SoftI2C(scl=Pin(self.SCL), sda=Pin(self.SDA), freq=FREQ)
        
    # Pomocná metoda pro čtení registru 8b LSB + 8b MSB + 8b PEC = 24b = 3B
    def read24(self, reg) -> int:
        # self.device.writeto(ADDR, bytes([reg]))
        self.LSB, self.MSB, self.PEC = self.device.readfrom_mem(ADDR, reg, 3)  # Přečte výsledek včetně PEC byte
        # print(f"msb: {self.MSB} lsb: {self.LSB} pec: {self.PEC}")
        return self.LSB | (self.MSB << 8)

    # Test na PEC
    def ok_test(self, reg) -> bool:
        to_test = [self.ADDR_WRITE, reg, self.ADDR_READ, self.LSB, self.MSB]  # složíme pole pro kontrolu součtu
        if (self.result_pec(to_test) != self.PEC):  # Otestujeme jestli vychází kontrolní součty
            print("Něco na senzoru zlobí")
            return False
        return True

    def emis(self):
        return self.read24(R_EMISSIVITY) / 65535

    # Pomocná metoda na výpočet PEC(Packet Error Code) dle CRC-8 standardu
    def result_pec(self, data_bytes):
        pec = 0x00  # začíná se s nulou
        for byte in data_bytes:
            pec ^= byte  # první XOR
            for _ in range(8):  # BYTE má 8 BITů
                if pec & 0x80:
                    pec = (pec << 1) ^ POLYNOM  # XOR s polynomem
                else:
                    pec <<= 1
                pec &= 0xFF
        return pec

    # Metoda na čtení teploty
    def __raw_temp(self, reg: int, secure: bool = False) -> float | bool:
        mezi = self.read24(reg)
        if secure and not(self.ok_test(reg)):
            raise ValueError("PEC mismatch")
        return mezi

    # Metoda čtení teploty v kelvinech
    def __raw_temp_kelvin(self, reg: int, secure: bool = False):
        return (self.__raw_temp(reg, secure) * 0.02)

    # Metoda čtení teploty ve stupních celsia
    def __raw_temp_celsius(self, reg: int, secure: bool = False):
        return self.__raw_temp_kelvin(reg, secure) - 273.15

    # Metoda čtení teploty ve Fahrenheitech
    def __raw_temp_fahrenheit(self, reg: int, secure: bool = False):
        return self.__raw_temp_kelvin(reg, secure)*9/5 - 459.67
    
    # Metody čtení teploty ambientu (teplota čidla)
    def t_ambient_c(self, secure=False):
        return self.__raw_temp_celsius( R_TA, secure)
    
    def t_ambient_k(self, secure=False):
        return self.__raw_temp_kelvin( R_TA, secure)

    def t_ambient_f(self, secure=False):
        return self.__raw_temp_fahrenheit( R_TA, secure)
    
    
    # Metody čtení teploty objektu
    def t_obj1_k(self, secure=False):
        return self.__raw_temp_kelvin(R_TO1, secure)

    def t_obj1_c(self, secure=False):
        return self.__raw_temp_celsius(R_TO1, secure)

    def t_obj1_f(self, secure=False):
        return self.__raw_temp_fahrenheit(R_TO1, secure)

    # Korekce teploty při jiné emisivitě.
    def correct_temperature_c(self, emissivity):
        Tm_K = self.t_obj1_k()
        Ta_K = self.t_ambient_k()
        num = Tm_K**4 - (1 - emissivity) * Ta_K**4
        corrected_K = (num / emissivity) ** 0.25
        return corrected_K - 273.15  # převod na Celsia