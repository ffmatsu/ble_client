#!/usr/bin/env python3

CHRC_HRM_HR_MEAS = '00002a37-0000-1000-8000-00805f9b34fb'
CHRC_HRM_SNSR_LOC = '00002a38-0000-1000-8000-00805f9b34fb'
# CHRC_HRM_CTRL_PT   = '00002a39-0000-1000-8000-00805f9b34fb'

CHRC_SNSR_LOC = '00002a5d-0000-1000-8000-00805f9b34fb'

CHRC_SPEED_CTRL_PT = '00002a55-0000-1000-8000-00805f9b34fb'
CHRC_SPEED_CSC_MEAS = '00002a5b-0000-1000-8000-00805f9b34fb'
CHRC_SPEED_CSC_FEAT = '00002a5c-0000-1000-8000-00805f9b34fb'

CHRC_DEVICE_SYSTEM_ID = '00002a23-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_MODEL = '00002a24-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_SERIAL = '00002a25-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_FW_REV = '00002a26-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_HW_REV = '00002a27-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_SW_REV = '00002a28-0000-1000-8000-00805f9b34fb'
CHRC_DEVICE_MANFUC = '00002a29-0000-1000-8000-00805f9b34fb'

CHRC_BATTERY_LEVEL = '00002a19-0000-1000-8000-00805f9b34fb'

SERVICE_GA = '00001800-0000-1000-8000-00805f9b34fb'
SERVICE_GAP = '00001801-0000-1000-8000-00805f9b34fb'
SERVICE_DEVICE = '0000180a-0000-1000-8000-00805f9b34fb'
SERVICE_HRM = '0000180d-0000-1000-8000-00805f9b34fb'
SERVICE_SPEED = '00001816-0000-1000-8000-00805f9b34fb'
SERVICE_BATT = '0000180f-0000-1000-8000-00805f9b34fb'


service_to_uuid_dict = {
    "SERVICE_SPEED": SERVICE_SPEED,
    "SERVICE_HRM": SERVICE_HRM,
}

uuid_to_key_dict = {
    # Services ---------------------
    # SERVICE_GA: "GA", # Not Control this program
    # SERVICE_GAP: "GAP", # Not Control this program
    SERVICE_DEVICE: "SERVICE_DEVICE",
    SERVICE_HRM: "SERVICE_HRM",
    SERVICE_SPEED: "SERVICE_SPEED",
    SERVICE_BATT: "SERVICE_BATT",
    # Chaaracteristic --------------
    # Heart Rate
    CHRC_HRM_HR_MEAS: "HR_MEAS",
    CHRC_HRM_SNSR_LOC: "SNSR_LOC",
    # Common characteristic
    CHRC_SNSR_LOC: "SNSR_LOC",
    # Cycling Speed and Cadence
    CHRC_SPEED_CTRL_PT: "CTRL_PT",  # Not Control
    CHRC_SPEED_CSC_MEAS: "CSC_MEAS",
    CHRC_SPEED_CSC_FEAT: "CSC_FEAT",
    # Device Information
    CHRC_DEVICE_SYSTEM_ID: "DEV_SYSTEM_ID",
    CHRC_DEVICE_MODEL: "DEV_MODEL",
    CHRC_DEVICE_SERIAL: "DEV_SERIAL",
    CHRC_DEVICE_FW_REV: "DEV_FW_REV",
    CHRC_DEVICE_HW_REV: "DEV_HW_REV",
    CHRC_DEVICE_SW_REV: "DEV_SW_REV",
    CHRC_DEVICE_MANFUC: "DEV_MANFUC",
    # Battery
    CHRC_BATTERY_LEVEL: "BATTERY_LEVEL",
}


def uuid_to_key(val):
    if val not in uuid_to_key_dict:
        return None
    return uuid_to_key_dict[val]


def is_valid_uuid(uuid):
    return uuid in uuid_to_key_dict
