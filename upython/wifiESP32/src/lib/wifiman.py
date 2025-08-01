# pyright: reportArgumentType=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalCall=false

import hashlib
import esp32
import network
import time
import _thread


class PBKDF2:
    """
    Implementace PBKDF2 podle https://en.wikipedia.org/wiki/PBKDF2
    """

    @staticmethod
    def hmac_sha1(key: bytes, msg: bytes) -> bytes:
        block_size = 64
        if len(key) > block_size:
            key = hashlib.sha1(key).digest()
        key = key + b"\x00" * (block_size - len(key))
        o_key_pad = bytes([b ^ 0x5C for b in key])
        i_key_pad = bytes([b ^ 0x36 for b in key])
        return hashlib.sha1(o_key_pad + hashlib.sha1(i_key_pad + msg).digest()).digest()

    @staticmethod
    def derive(
        password: str | bytes,
        salt: str | bytes,
        iterations: int = 4096,
        dklen: int = 256,
        prf: callable | None = None,  # přidáno
        progress_cb: callable | None = None,
    ) -> bytes:
        """
        Metoda na vytvoření DK(Derived Key)
        Args:
            password: heslo
            salt: sůl
            iterations: kolikrát se má derivovat
            dklen: požadovaná délka klíče. Pozor uvádí se v bitech
            progress_cb: callback fce na výpis průchodu
        Return: DK klíč
        """
        if isinstance(password, str):
            password = password.encode()
        if isinstance(salt, str):
            salt = salt.encode()
        dklen, remainder = divmod(dklen, 8)
        if remainder:
            raise ValueError(f"Lenght {dklen} must be divided by 8")

        # def hmac_sha1(key: bytes, msg: bytes) -> bytes:
        #     block_size = 64
        #     if len(key) > block_size:
        #         key = hashlib.sha1(key).digest()
        #     key = key + b"\x00" * (block_size - len(key))
        #     o_key_pad = bytes([b ^ 0x5C for b in key])
        #     i_key_pad = bytes([b ^ 0x36 for b in key])
        #     return hashlib.sha1(
        #         o_key_pad + hashlib.sha1(i_key_pad + msg).digest()
        #     ).digest()

        hlen = 20  # SHA1 digest length
        l = (dklen + hlen - 1) // hlen
        dk = b""
        done = 0
        tot = iterations * l

        try:
            for i in range(1, l + 1):
                block = salt + i.to_bytes(4, "big")
                # u = PBKDF2.hmac_sha1(password, block)
                # if not prf:
                #     prf = PBKDF2.hmac_sha1
                u = prf(password, block)
                t = bytearray(u)
                for _ in range(1, iterations):
                    u = PBKDF2.hmac_sha1(password, u)
                    for j in range(len(t)):
                        t[j] ^= u[j]
                    done += 1
                    if progress_cb and done % 128 == 0:
                        progress_cb(int(100 * done / tot))
                dk += bytes(t)
        except Exception as e:
            raise RuntimeError(f"Big problem {e}")

        if progress_cb:
            progress_cb(100)
        return dk[:dklen]

    @staticmethod
    def wpa_psk(ssid: str, password: str, progress_cb: callable | None = None) -> bytes:
        """Returns WPA2 PSK (64-char hex string) from SSID and password."""
        return PBKDF2.derive(password, ssid, 4096, 256, PBKDF2.hmac_sha1, progress_cb)


class PSKSTORAGE:
    """
    Třída na manipulaci ssid - psk v perzistentní paměti
    """

    @staticmethod
    def store_psk(ssid: str, passwd: str) -> bool:
        """
        Na základě ssid a hesla vypočítá psk a uloží do NVS
        Args:
            ssid: název sítě jako klíč
            passwd: heslo z kterého bude vytvořen psk a ten uložen
        Return: bool podle úspěchu
        """
        try:
            psk = PBKDF2.wpa_psk(ssid, passwd)
            PSKSTORAGE.write(ssid, psk)
            return True
        except Exception as e:
            print(f"Store {ssid} Error:{e}")
            return False

    @staticmethod
    def write(ssid: str, psk: str) -> bool:
        """
        Uloží ssid jako klíč a psk|heslo v raw formátu
        Args:
            ssid: název sítě
            psk: psk (PreSharedKey) | password
        Return: bool podle úspěchu
        """
        try:
            ulozeny = PSKSTORAGE.read(ssid)
            if ulozeny == bytes(psk, "UTF8"):
                print("není třeba zapisovat, už to tam je.")
                return True
            nvs = esp32.NVS("ssid")
            nvs.set_blob(ssid, psk)
            nvs.commit()
            print("Zapsáno")
            return True
        except Exception as e:
            print(f"Write {ssid} Error: {e}")
            return False

    @staticmethod
    def read(ssid: str) -> bool | bytes:
        """
        Vrátí raw psk kdanému ssid. Pokud je ssid neznámé vrátí False
        Args:
            ssid: název sítě
        Return:
            psk v raw formátu nebo False
        """
        try:
            nvs = esp32.NVS("ssid")
            psk = bytearray(1024)
            delka = nvs.get_blob(ssid, psk)
            psk = psk[:delka]
            return bytes(psk)
        except Exception as e:
            print(f"Read {ssid} Error: {e}")
            return False

    @staticmethod
    def load_psk(ssid: str) -> str:
        """
        Přiřadí psk k ssid. Pokud je ssid neznámé vrátí False
        Args:
            ssid: název sítě
        Return:
            psk v text formátu
        """
        psk = PSKSTORAGE.read(ssid)
        if isinstance(psk, bool):
            raise RuntimeError("Chybka")
        return psk.hex()

    @staticmethod
    def remove_psk(ssid: str) -> bool:
        """
        Vymaže záznam daného ssid z NVS
        Args:
            ssid: název sítě
        Return:
            bool podle úspěchu
        """
        try:
            nvs = esp32.NVS("ssid")
            nvs.erase_key(ssid)
            nvs.commit()
            return True
        except Exception as e:
            print(f"Remove {ssid} Error: {e}")
            return False


# def wifi_connect(ssid: str, callback_fc: callable | None = None) -> any:
#     psk = PSKSTORAGE.load_psk(ssid)  # Vrací psk nebo False
#     if not psk:
#         if callback_fc:
#             psk = callback_fc(ssid)
#         else:
#             raise RuntimeError(f"Unknow {ssid}")
#     wlan = network.WLAN(network.STA_IF)
#     wlan.active(True)
#     if not wlan.isconnected():
#         print(f"Connecting to {ssid}...")
#         wlan.connect(ssid, psk)
#         for _ in range(20):
#             if wlan.isconnected():
#                 break
#             time.sleep(1)
#         else:
#             raise RuntimeError("Unable connect Wi-Fi")
#     print("Wi-Fi connect:", wlan.ifconfig())
#     return wlan


def wifi_connect(
    ssid: str,
    password: str | bytes | None = None,
    hostname: str = "moje_esp32",
    callback_fc: callable | None = None,
    timeout: int = 30,
) -> network.WLAN:
    """
    Připojí se k Wi-Fi síti

    Args:
        ssid: Název sítě
        hostname: pod jakým názvem má být MCU viditelné
        callback_fc: Funkce pro získání hesla pokud není uloženo
        timeout: Timeout pro připojení v sekundách

    Returns:
        network.WLAN objekt

    Raises:
        RuntimeError: Při chybě připojení nebo neznámé síti
    """
    # Získání hesla
    psk = PSKSTORAGE.load_psk(ssid)
    if not psk:
        if callback_fc:
            psk = callback_fc(ssid, password)
            if not psk:  # Callback může vrátit None/False
                raise RuntimeError(f"Heslicko")
# print("read2:", PSKSTORAGE.read("fake"))
# print("load2:", PSKSTORAor(f"No password provided for {ssid}")
        else:
            raise RuntimeError(f"Unknown network: {ssid}")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Zkontroluj, jestli už nejsme připojeni ke správné síti
    if wlan.isconnected():
        current_ssid = wlan.config("essid")
        if current_ssid == ssid:
            print(f"Already connected to {ssid}")
            return wlan
        else:
            print(f"Disconnecting from {current_ssid}")
            wlan.disconnect()

    try:
        print(f"Connecting to {ssid}...")
        wlan.config(dhcp_hostname=hostname)
        wlan.connect(ssid, psk)

        # Čekání na připojení s timeoutem
        for _ in range(timeout):
            if wlan.isconnected():
                config = wlan.ifconfig()
                print(f"Wi-Fi connected: {config[0]}")  # IP adresa
                return wlan
            time.sleep(1)

        # Timeout - cleanup a výjimka
        raise RuntimeError(f"Connection timeout after {timeout}s")

    except Exception as e:
        # Cleanup při jakékoli chybě
        wlan.active(False)
        raise RuntimeError(f"Wi-Fi connection failed: {e}")
