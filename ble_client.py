#!/usr/bin/env python3
__version__ = "1.0.0"

import threading
import dbus
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import os
import time
import signal
import json
import queue

import ble_uuid as UUID

from ble_util import LOG
import ble_parser

from dbus.mainloop.glib import DBusGMainLoop


bus = None
mainloop = None

recv_message_queue = queue.Queue()

BLUEZ_SERVICE_NAME = 'org.bluez'

IFACE_DBUS_OM = 'org.freedesktop.DBus.ObjectManager'
IFACE_DBUS_PROP = 'org.freedesktop.DBus.Properties'

IFACE_ADAPTER = 'org.bluez.Adapter1'
IFACE_DEVICE = 'org.bluez.Device1'
IFACE_GATT_SERVICE = 'org.bluez.GattService1'
IFACE_GATT_CHRC = 'org.bluez.GattCharacteristic1'

PATH_ADAPTER = '/org/bluez/hci0'


def interfaces_removed_cb(object_path, interfaces):
    LOG.debug("{}: {}".format(object_path, interfaces))


'''
BlueZ Management
'''


def fetch_object(path):
    try:
        return bus.get_object(BLUEZ_SERVICE_NAME, path)
    except Exception as e:
        LOG.error("faital error in fetch_object({}): {}".format(path, str(e)))
        mainloop.quit()


def fetch_property(path, iface):
    try:
        obj = fetch_object(path)
        obj_props = obj.GetAll(iface, dbus_interface=IFACE_DBUS_PROP)
    except Exception as e:
        LOG.error("failed fetch_property: {}".format(e))
        obj_props = None

    return obj_props


def reset_bluetooth_power():
    adapter = bus.get_object(BLUEZ_SERVICE_NAME, PATH_ADAPTER)
    adapter_props = dbus.Interface(adapter, IFACE_DBUS_PROP)

    try:
        adapter_props.Set(IFACE_ADAPTER, "Powered", dbus.Boolean(0))
        LOG.info("power off")
        time.sleep(3)
        adapter_props.Set(IFACE_ADAPTER, "Powered", dbus.Boolean(1))
        LOG.info("power on")
        time.sleep(3)
    except Exception as e:
        LOG.error("can't reset power state:{}".format(repr(e)))
        exit()


def get_object_manager():
    om = dbus.Interface(fetch_object('/'), IFACE_DBUS_OM)
    return om


def get_managed_objects():
    try:
        om = get_object_manager()
        objects = om.GetManagedObjects()
        return objects
    except Exception as e:
        LOG.error("faital error in get_managed_objects(): {}".format(str(e)))
        mainloop.quit()


def fetch_child_objs(root_path, iface):
    objects = get_managed_objects()
    paths = []

    for path, interfaces in objects.items():
        if iface not in interfaces.keys():
            continue
        dir_path = os.path.dirname(path)  # to get device path
        if dir_path != root_path:
            continue

        obj_props = fetch_property(path, iface)
        if not obj_props:
            return []

        uuid = obj_props['UUID']
        paths.append([path, uuid])

    return paths


def read_value_cb(value):
    value_str = ''.join([chr(byte) for byte in value])
    value_str = value_str.encode('utf-8')
    value_array = [int(byte) for byte in value]
    LOG.debug("READ: -> {} : {}".format(value_str, value_array))


read_error_flg = False


def read_value_error_cb(error):
    LOG.error("read value error: {}".format(error))
    global read_error_flg
    read_error_flg = True


def parse_message_thread():
    global path_id_dict
    global recv_message_queue

    ch = 5
    LOG.info("start thread")
    while True:
        if not recv_message_queue.empty():
            path, value = recv_message_queue.get()

            LOG.debug("{} {}".format(path, value))
            id = path_id_dict.get(path, None)
            LOG.debug(id)
            uuid = path_uuid_dict.get(path, None)
            LOG.debug(uuid)

            if uuid not in ble_parser.uuid_to_parser_dict:
                LOG.warning("Unknown uuid in cb_table: {}".format(uuid))
                return

            parse_func = ble_parser.uuid_to_parser_dict[uuid]
            parse_func(id, value)  # {id: [ payload, data_type ]}

        else:
            time.sleep(0.1)


def device_prop_changed(interface, changed, invalidated, path):
    if interface != IFACE_DEVICE:
        return
    LOG.debug(path)
    LOG.debug(changed)


def property_changed(interface, changed, invalidated, path):
    if interface != IFACE_GATT_CHRC:
        return

    if not len(changed):
        return

    notify = changed.get('Notifying', None)
    value = changed.get('Value', None)

    if notify:
        LOG.info("{} Notifying = {}".format(path, notify))
        return

    if not value:
        LOG.warning("value is None")
        return

    recv_message_queue.put((path, value))


path_id_dict = dict()
path_uuid_dict = dict()


def update_id_uuid_list(profile_key, chrc_key, path, uuid):
    global path_id_dict
    global path_uuid_dict

    if not profile_key:
        profile_key = "UNKNOWN"

    id = profile_key + '_' + chrc_key

    path_id_dict[path] = id.lower()
    path_uuid_dict[path] = uuid


def start_notify_cb():
    LOG.info('notifications enabled')


def start_notify_error_cb(error):
    LOG.error('D-Bus call failed: ' + str(error))


def configure_chrc(service_path, profile_key):
    LOG.info("====================")
    LOG.info("arg={}".format(service_path))

    chrcs = fetch_child_objs(service_path, IFACE_GATT_CHRC)

    for path, uuid in chrcs:
        chrc_key = UUID.uuid_to_key(uuid)
        LOG.debug("{} {} {}".format(uuid, chrc_key, path))
        if chrc_key:
            LOG.info("============")
            LOG.info("{} {} {}".format(uuid, chrc_key, path))
            update_id_uuid_list(profile_key, chrc_key, path, uuid)
            props = fetch_property(path, IFACE_GATT_CHRC)
            flags = props.get('Flags', {})
            for flag in flags:
                LOG.info("Flag: {}".format(flags))
                if flag == 'read':
                    chrc_obj = fetch_object(path)
                    chrc_obj.ReadValue({}, reply_handler=read_value_cb,
                                       error_handler=read_value_error_cb,
                                       dbus_interface=IFACE_GATT_CHRC)
                if flag == 'notify' or flag == 'indicate':
                    notify = props['Notifying']
                    if notify == 0:
                        LOG.info("start notify key={}".format(chrc_key))
                        chrc_obj = fetch_object(path)
                        chrc_obj.StartNotify(reply_handler=start_notify_cb,
                                             error_handler=start_notify_error_cb,
                                             dbus_interface=IFACE_GATT_CHRC)

    global path_id_dict
    global path_uuid_dict
    LOG.debug(json.dumps(path_id_dict, indent=2))
    LOG.debug(json.dumps(path_uuid_dict, indent=2))


def configure_service(device_path, profile_key):
    LOG.info("**********************************************")
    LOG.debug("args=({}, {})".format(device_path, profile_key))

    services = fetch_child_objs(device_path, IFACE_GATT_SERVICE)

    count_service = 0
    for path, uuid in services:
        service_key = UUID.uuid_to_key(uuid)
        LOG.debug("service: {} {} ".format(uuid, path))

        if service_key:
            count_service += 1
            LOG.info("detect service:{} {} {}".format(uuid, service_key, path))
            configure_chrc(path, profile_key)

    LOG.info("count_service:{}".format(count_service))

    global read_error_flg
    if read_error_flg:
        read_error_flg = False
        LOG.warning("can't configure service {}".format(profile_key))
        return False

    if count_service == 0:
        LOG.warning("can't detect service {} in {}".format(profile_key, device_path))
        return False

    return True


def service_thread(device_path, profile_key):
    LOG.info("*********** enter to loop")
    is_configured_service = False
    while True:
        time.sleep(3)

        if not is_connected_device(device_path):
            LOG.info("not connected {}".format(profile_key))
            is_configured_service = False
            continue

        is_resolved = is_service_resolved(device_path)
        LOG.debug("service resolved {}: {}".format(device_path, is_resolved))

        if (not is_resolved):
            LOG.info("service is not resolved, waiting...")
            continue

        if not is_configured_service:
            LOG.debug("configure_service({} {})".format(device_path, profile_key))
            if configure_service(device_path, profile_key):
                is_configured_service = True
                LOG.info("configured service success: {}".format(device_path))


'''
Device Interface
'''


def is_connected_device(device_path):
    dev_props = fetch_property(device_path, IFACE_DEVICE)

    if dev_props is None:
        return False

    is_connected = dev_props.get("Connected", 0)
    if is_connected == 1:
        return True
    return False


def is_alive_device(device_path):
    dev_props = fetch_property(device_path, IFACE_DEVICE)

    if dev_props is None:
        return False

    rssi = dev_props.get("RSSI", None)
    if rssi:
        LOG.info("RSSI={} {}".format(rssi, device_path))
        return True
    else:
        LOG.warning("no RSSI {}".format(device_path))
        return False
    return False


def is_service_resolved(device_path):
    dev_props = fetch_property(device_path, IFACE_DEVICE)
    if dev_props is None:
        return False

    is_resolved = dev_props.get("Connected", 0)
    if is_resolved == 1:
        return True
    return False


is_connecting = False


def device_connect_cb():
    LOG.info("connection successful")

    global is_connecting
    is_connecting = False


def device_connect_error_cb(error):
    LOG.warning('device_connect_error_cb(error): ' + str(error))
    time.sleep(1)
    global is_connecting
    is_connecting = False


def device_connect(device_path, key):
    # Connect Device if no connected
    dev_object = fetch_object(device_path)
    dev_iface = dbus.Interface(dev_object, IFACE_DEVICE)

    global is_connecting

    if is_connected_device(device_path):
        LOG.info("already connected: {}".format(device_path))
        return False

    LOG.info("not connected, Try to connect:{}".format(device_path))
    try:
        is_connecting = True
        dev_iface.Connect(reply_handler=device_connect_cb,
                          error_handler=device_connect_error_cb,
                          dbus_interface=IFACE_DEVICE)
    except Exception as e:
        LOG.error("connection error {}, {}".format(device_path, e))
        time.sleep(1)
        is_connecting = False
        return False
    count = 0
    while(is_connecting):
        LOG.info("connecting....{}".format(device_path))
        count += 1
        if count > 15:
            LOG.error("connection timeout (faital error)")
            return False
        time.sleep(2)
    LOG.info("connection success: {}".format(key))
    if is_connected_device(device_path):
        return wait_services_resolved(device_path)

    return False


def wait_services_resolved(device_path):
    # to wait services resolved
    count = 0
    while(True):
        is_resolved = is_service_resolved(device_path)
        LOG.debug("service resolved {}: {}".format(device_path, is_resolved))

        if (is_resolved):
            LOG.info("Service resolved! :{}".format(device_path))
            return True

        if(is_connected_device(device_path) is False):
            LOG.error("Waiting service resolved, but disconnected")
            return False
        LOG.info("waiting service resolved...")
        count += 1

        if count > 30:
            LOG.warning("wait service timeout")
            return False

        time.sleep(1)


'''
Thread
'''


def check_connection_state(connection_table):

    result = True
    for key, path in connection_table.items():
        if is_connected_device(path) is False:
            result = False
            break

    return result


def device_connect_thread(connection_table):

    adapter = fetch_object(PATH_ADAPTER)
    adapter_if = dbus.Interface(adapter, IFACE_ADAPTER)

    while True:
        if check_connection_state(connection_table):
            LOG.info("all device is connected")
            adapter_props = fetch_property(PATH_ADAPTER, IFACE_ADAPTER)
            discovering = adapter_props.get('Discovering', False)

            if discovering:
                adapter_if.StopDiscovery()
                LOG.info("stop SCAN ***************")

            time.sleep(5)
            continue

        # Scan devices
        adapter_props = fetch_property(PATH_ADAPTER, IFACE_ADAPTER)
        discovering = adapter_props.get('Discovering', False)

        if not discovering:
            try:
                adapter_if.StartDiscovery()
                LOG.info("start SCAN ***************")
            except Exception as e:
                LOG.warning("Scan error: {}".format(str(e)))

        # Connect device if device is alive
        for profile_key, dev_path in connection_table.items():

            if is_connected_device(dev_path) is True:
                LOG.info("already connected {}".format(dev_path))
                continue

            if not is_alive_device(dev_path):
                LOG.info("can't find device near side: {}".format(dev_path))
                continue

            LOG.info("start connect {}".format(dev_path))
            device_connect(dev_path, profile_key)

        time.sleep(2)


def configure_device():
    objects = get_managed_objects()

    all_devices = (str(path) for path, interfaces in objects.items()
                   if IFACE_DEVICE in interfaces.keys())

    connection_table = {}
    for device_path in all_devices:
        LOG.debug("------------")
        LOG.debug(device_path)
        dev = objects[device_path]
        properties = dev[IFACE_DEVICE]
        uuids = properties["UUIDs"]
        for uuid in uuids:
            LOG.debug(uuid)
            if uuid == UUID.SERVICE_HRM:
                connection_table["HRM"] = device_path
            if uuid == UUID.SERVICE_SPEED:
                connection_table["SPEED"] = device_path

    LOG.info("connection_table: {}".format(connection_table))

    if len(connection_table) == 0:
        LOG.error("No supported devices are registered")
        time.sleep(5)
        exit()

    for key, path in connection_table.items():
        LOG.info("{}:{}".format(key, path))

    for profile_key, device_path in connection_table.items():
        LOG.info("kick service_thread({},{})".format(profile_key, device_path))
        t = threading.Thread(target=service_thread,
                             args=(device_path, profile_key))
        t.setDaemon(True)
        t.start()

    LOG.debug("kick device_connect_thread({})".format(connection_table))
    t = threading.Thread(target=device_connect_thread,
                         args=([connection_table]))
    t.setDaemon(True)
    t.start()
    return True


def interfaces_added(path, interfaces):

    LOG.info(path)
    LOG.info(interfaces)
    properties = interfaces["org.bluez.Device1"]

    if not properties:
        return


def signalHandler(signum, frame):
    LOG.info("signum: {}".format(signum))
    mainloop.quit()
    LOG.info("exit bye")
    exit()


def main():
    # signal.signal(signal.SIGINT, lambda n, f: mainloop.quit())
    # signal.signal(signal.SIGTERM, lambda n, f: mainloop.quit())

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    # Set up the main loop.
    DBusGMainLoop(set_as_default=True)
    global bus
    bus = dbus.SystemBus()

    global mainloop
    GObject.threads_init()
    mainloop = GObject.MainLoop()

    reset_bluetooth_power()

    om = get_object_manager()
    om.connect_to_signal('InterfacesRemoved', interfaces_removed_cb)

    bus.add_signal_receiver(interfaces_added,
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="InterfacesAdded")

    bus.add_signal_receiver(property_changed, bus_name="org.bluez",
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="PropertiesChanged",
                            path_keyword="path")
    bus.add_signal_receiver(device_prop_changed,
                            dbus_interface="org.freedesktop.DBus.Properties",
                            signal_name="PropertiesChanged",
                            arg0="org.bluez.Device1",
                            path_keyword="path")

    LOG.debug("kick parse_message_thread()")
    t = threading.Thread(target=parse_message_thread, args=([]))
    t.setDaemon(True)
    t.start()

    configure_device()

    LOG.info("mainloop.run()")
    mainloop.run()


if __name__ == '__main__':
    main()
