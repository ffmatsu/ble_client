#!/usr/bin/env python3

import ble_uuid as UUID
from ble_util import LOG

'''
parse message
'''


def parse_string(id, value):
    value_str = ''.join([chr(byte) for byte in value])
    # value_str = value_str.encode('utf-8')
    LOG.info("{}\t-> {}".format(id, value_str))


def parse_integer(id, value):
    value_int = int.from_bytes(value, byteorder='little', signed=False)

    LOG.info("{}\t -> {}".format(id, value_int))


def parse_integer_signed(id, value):
    value_int = int.from_bytes(value, byteorder='little', signed=True)

    LOG.info("{}\t -> {}".format(id, value_int))


def parse_binary(id, value):
    value_array = [int(byte) for byte in value]
    LOG.info("{}\t-> {}".format(id, value_array))
    value = bytearray(value)  # Dbus.array -> byte array


def parse_speed_csc_meas(id, value):

    flags = value[0]

    wheel_status = flags & 0x01

    if wheel_status != 1:
        LOG.warning("no wheel flag")
        return

    tmp = value[1:5]
    wheel_rev = int.from_bytes(tmp, byteorder='little', signed=False)

    tmp = value[5:7]
    update_time = int.from_bytes(tmp, byteorder='little', signed=False)
    update_time /= 1024.0

    LOG.info("{}\t-> wh_rev:{}\tupdate_time:{}".
              format(id, wheel_rev, update_time))


def parse_hrm_meas(id, value):

    flags = value[0]

    hr_value_fmt = flags & 0x01

    if hr_value_fmt == 1:
        tmp = value[1:3]
        hrm_meas = int.from_bytes(tmp, byteorder='little', signed=False)
    else:
        tmp = value[1]
        hrm_meas = int(tmp)

    LOG.info("{}\t-> hr_meas = {} bpm".format(id, hrm_meas))


def from_bytes_sint8(value):
    if value == 0x80:
        return 0x80
    else:
        return int.from_bytes([value], byteorder='little', signed=True)


def from_bytes_sint16(value):
    if value[0] == 0x00 and value[1] == 0x80:
        return 0x8000
    else:
        return int.from_bytes(value[0:2], byteorder='little', signed=True)


def parse_none(id, value):
    LOG.error("Unknown UUID, id={}".format(id))

    return {id: [None, None]}


uuid_to_parser_dict = {
    # Heart Rate
    UUID.CHRC_HRM_HR_MEAS: parse_hrm_meas,
    UUID.CHRC_HRM_SNSR_LOC: parse_integer,
    # Common characteristic
    UUID.CHRC_SNSR_LOC: parse_integer,
    # Cycling Speed and Cadence
    UUID.CHRC_SPEED_CSC_MEAS: parse_speed_csc_meas,
    UUID.CHRC_SPEED_CSC_FEAT: parse_integer,
    # Device Information
    UUID.CHRC_DEVICE_SYSTEM_ID: parse_integer,
    UUID.CHRC_DEVICE_MODEL: parse_string,
    UUID.CHRC_DEVICE_SERIAL: parse_string,
    UUID.CHRC_DEVICE_FW_REV: parse_string,
    UUID.CHRC_DEVICE_HW_REV: parse_string,
    UUID.CHRC_DEVICE_SW_REV: parse_string,
    UUID.CHRC_DEVICE_MANFUC: parse_string,
    # Battery
    UUID.CHRC_BATTERY_LEVEL: parse_integer,
}
