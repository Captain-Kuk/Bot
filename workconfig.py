import configparser
import os


def create_config(path):
    """
    Create a config file
    """
    config = configparser.ConfigParser()

    config.add_section("PathToDocs")
    config.set("PathToDocs", "path", "e:\\tests\\docs\\")

    config.add_section("TokenForTelegramBot")
    config.set("TokenForTelegramBot", "token", "1610997177:AAGmC3dTfxC6D_ZmHvoRn8Fodiq_I2DUtVI")
    with open(path, "w") as config_file:
        config.write(config_file)


def read_config(path):
    """
    Create, read, update, delete config
    """
    if not os.path.exists(path):
        create_config(path)
    config = configparser.ConfigParser()
    config.read(path)
    return config
