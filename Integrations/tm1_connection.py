from TM1py import TM1Service
from Core.settings import TM1_HOST, TM1_PORT, TM1_USER, TM1_PASSWORD, TM1_SSL

tm1_config = {
    "address" : TM1_HOST,
    "port"    : int(TM1_PORT),
    "user"    : TM1_USER,
    "password": TM1_PASSWORD,
    "ssl"     : TM1_SSL,
}

def get_tm1():
    return TM1Service(**tm1_config)