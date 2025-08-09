from machine import Pin, SoftI2C
from micropython import const


# mlx90614 datasheet at https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf

ADDR = const(0x5A)  # Default I2C address of MLX90614
FREQ = const(50_000)  # Communication frequency

# RAM registers
R_RAW_IR1 = const(0x04) # Raw value register for object1
R_RAW_IR2 = const(0x05) # Raw value register for object2
R_TA = const(0x06) # Ambient (sensor) temperature register
R_TO1 = const(0x07) # Object1 temperature register
R_TO2 = const(0x08) # Object2 temperature register

# EEPROM registers. For use according to datasheet chapter 4.1.4.3.6 commands must be with 001* **** = (0x20)
R_EMISSIVITY = const(0x20 | 0x04) # Emissivity register is at 0x04 OR 0x20

# CRC-8 spec
POLYNOM = const(0x07)


class mlx90614:
    """
    class mlx90614
        args:
            SDA: Pin Serial DAta
            SCL: Pin Serial CLock
            SA: Slave address
            freq: maximum frequency for SCL
    """
    def __init__(self, SDA: int, SCL: int, SA: int = ADDR, freq: int = FREQ) -> None:
        self.SDA = SDA
        self.SCL = SCL
        self.LSB = 0
        self.MSB = 0
        self.PEC = 0
        self.addr = SA
        self.freq = freq
        self.ADDR_WRITE = (
            SA << 1 | 0
        )  # According to specification, shift 7bit address left by one bit plus 0 at the end for write
        self.ADDR_READ = (
            SA << 1 | 1
        )  # According to specification, shift 7bit address left by one bit plus 1 at the end for read
        self.device = SoftI2C(scl=Pin(self.SCL), sda=Pin(self.SDA), freq=self.freq)
        
    # Helper method for reading 8b LSB + 8b MSB + 8b PEC = 24b = 3B register
    def read24(self, reg: int) -> int:
        """
        Reads 3 Bytes from register. Stores result in order LSB, MSB and PEC
        args:
            reg: int register address

        return: 16b MSB with LSB
        """
        self.LSB, self.MSB, self.PEC = self.device.readfrom_mem(self.addr, reg, 3)  # Reads result including PEC bytes
        return self.LSB | (self.MSB << 8)

    # PEC test
    def ok_test(self, reg) -> bool:
        """
        Compares stored PEC from last operation with calculated PEC
        args:
            reg: int register address
        return: bool
        """
        to_test = [self.ADDR_WRITE, reg, self.ADDR_READ, self.LSB, self.MSB]  # Create array for checksum verification
        if (self.result_pec(to_test) != self.PEC):  # Test if checksums match
            print("WRONG PEC!")
            return False
        return True

    @property
    def emissivity(self) -> float:  # Reads "hardcoded" emissivity from register.
        """
        return: float in range 0.01 ~ 1.0 stored in sensor register
        """
        return self.read24(R_EMISSIVITY) / 65535

    # Helper method for calculating PEC (Packet Error Code) according to CRC-8 standard
    def result_pec(self, data_bytes):
        """
        Calculates PEC from received byte array according to CRC-8 standard
        args:
            data_bytes: byte array
        return: PEC byte
        """
        pec = 0x00  # Start with zero
        for byte in data_bytes:
            pec ^= byte  # First XOR
            for _ in range(8):  # BYTE has 8 BITs
                if pec & 0x80:
                    pec = (pec << 1) ^ POLYNOM  # XOR with polynomial
                else:
                    pec <<= 1
                pec &= 0xFF
        return pec


    # Method for reading temperature in kelvins
    def raw_temp(self, reg: int, secure: bool = False) -> float:
        """
        Method for reading temperature in kelvins. According to `secure` parameter, performs (or not) PEC verification.
        PEC verification calculation is somewhat resource intensive for MCU. Not needed for most hobby projects.
        Do not use with R_RAW_IR* registers! These don't contain temperatures but radiation units.
        args:
            reg: int ~ register
            secure: bool ~ True if PEC verification should be performed
        return: float ~ value in kelvins
        When secure is True and PEC doesn't match, raises exception.
        """
        mezi = self.read24(reg)
        if mezi & 0x8000:
            raise ValueError("MLX90614: invalid data (error flag set)")

        if secure and not(self.ok_test(reg)):
            raise ValueError("PEC mismatch")

        return mezi * 0.02


    # Method for reading ambient (sensor) temperature
    def t_ambient(self, secure=False) -> float:
        """
        Returns ambient (sensor) temperature
        args:
            secure: bool ~ whether to perform PEC verification. Default is False
        """
        return self.raw_temp(R_TA, secure)
    
    # Methods for reading object temperature
    def t_obj1(self, secure=False):
        """
        Returns object1 temperature
        args:
            secure: bool ~ whether to perform PEC verification. Default is False
        """
        return self.raw_temp(R_TO1, secure)

    def t_obj2(self, secure=False):
        """
        Only for dual zone sensors.
        Returns object2 temperature
        args:
            secure: bool ~ whether to perform PEC verification. Default is False
        """
        return self.raw_temp(R_TO2, secure)
    

    def to_C(self, temp: float) -> float:
        """
        Converts temperature from kelvin to celsius
        args:
            temp: float ~ value in kelvins
        return: float ~ value in °C
        """
        return temp - 273.15

    def to_F(self, temp: float) -> float:
        """
        Converts temperature from kelvin to fahrenheit
        args:
            temp: float ~ value in kelvins
        return: float ~ value in F
        """
        return temp *9/5 - 459.67
    
    # Temperature correction for different emissivity
    def correct_temperature(self, emissivity: float, secure=False) -> float:
        """
        Based on ambient temperature and object1 temperature, calculates correct
        object temperature according to given emissivity. For correct calculation,
        manufacturer-set emissivity should be 1.
        args:
            emissivity: float ~ 0.01–1.0
            secure: bool ~ whether to perform PEC verification. Default is False
        return: float ~ temperature in kelvin
        This method saves limited writes to sensor's EEPROM.
        """
        if not (0.01 <= emissivity <= 1.0):
            raise ValueError("emissivity must be 0.01–1.0")
        Tm_K = self.raw_temp(R_TO1, secure)
        Ta_K = self.raw_temp(R_TA, secure)
        num = Tm_K**4 - (1 - emissivity) * Ta_K**4
        return (num / emissivity) ** 0.25