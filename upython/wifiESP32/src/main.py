from wifiman import PBKDF2, PSKSTORAGE, wifi_connect

ssid = "Dvur-NET"

# použité ssid a hesla:
# fake, heslicko

# ssid = input("SSID:")
# password = input("Heslo:")


def my_progress(procenta):
    print("Průběh:", procenta, "%", end="\r")
    if procenta == 100:
        print("")


# print(PBKDF2.wpa_psk(ssid, password, my_progress))
# PSKSTORAGE.store_psk(ssid, password)
print("read1:", PSKSTORAGE.read(ssid))
print("load1:", PSKSTORAGE.load_psk(ssid))
# PSKSTORAGE.write("fake", "Heslicko")
# print("read2:", PSKSTORAGE.read("fake"))
# print("load2:", PSKSTORAGE.load_psk("fake"))
wifi_connect(ssid)
