import json, requests
import logging
import socket, re
from time import sleep
import netifaces as ni

import datetime, sys, traceback, os
from asgiref.sync import sync_to_async

from django.conf import settings as conf_settings

from manager.dbmodels.vetti import Vetti
from processors.searchvetti import SearchVetti
from tools import Tools


import asyncio
import logging
import socket
import xml.etree.ElementTree as ET
from time import time
from typing import Dict, Sequence, Type

from async_upnp_client.client import UpnpRequester, UpnpStateVariable
from async_upnp_client.const import (
    STATE_VARIABLE_TYPE_MAPPING,
    DeviceInfo,
    ServiceInfo,
    StateVariableTypeInfo, EventableStateVariableTypeInfo,
)

from async_upnp_client.server import UpnpServer, UpnpServerDevice, UpnpServerService, callable_action, \
    UpnpEventableStateVariable, EventSubscriber, create_state_var

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger("emulated_device")
LOGGER_SSDP_TRAFFIC = logging.getLogger("async_upnp_client.traffic")
LOGGER_SSDP_TRAFFIC.setLevel(logging.WARNING)
SOURCE = ("127.0.0.1", 0)  # The script will set dynamically
HTTP_PORT = 1900

logger = logging.getLogger('Alexa Plug')
logger.setLevel(logging.DEBUG)
if os.isatty(0):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
else:
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    logger.addHandler(handler)

requests.packages.urllib3.disable_warnings()


class AlexaPlug():
    log_source = "Alexa Plug"

    def __init__(self):
        pass

    def process(self):
        logger.info("Alexa Plug")

        pid = str(os.getpid())
        pidfile = "/tmp/alexa_plug.pid"

        if os.path.isfile(pidfile):
            with open(pidfile, 'r') as f:
                d = f.read()
                fpid = -1
                if d.strip() != '':
                    fpid = int(d)

            if Tools.pid_is_running(fpid):
                logger.info(f'{pidfile} already exists and process is running, exiting')
                sys.exit()
            else:
                logger.info(f'{pidfile} already exists but process is not running, continuing...')

        with open(pidfile, "w") as f:
            f.write(f'{pid}\n')

        try:
            self.start_plug()

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error = traceback.format_exception(exc_type, exc_value, exc_traceback)
            err_txt = '%s\n\n' % exc_value
            for e in error:
                err_txt += str(e.strip('\n'))

            logger.error(err_txt)
        finally:
            os.unlink(pidfile)

    async def async_main(self, server: UpnpServer) -> None:
        """Main."""
        await server.async_start()

        while True:
            await asyncio.sleep(3600)

    async def async_wait(self) -> None:
        while True:
            await asyncio.sleep(3600)

    def get_state(self, vetti_id: str) -> bool:
        vetti = Vetti.objects.filter(enabled=True, vetti_id=vetti_id).first()
        return vetti.armed if vetti is not None else False

    def set_state(self, vetti_id: str, state: bool):
        vetti = Vetti.objects.filter(enabled=True, vetti_id=vetti_id).first()
        if vetti is not None:
            vetti.armed = state
            vetti.save()
            SearchVetti.update_state(vetti)

    def start_plug(self):
        try:
            top_self = self
            for central in Vetti.objects.filter(enabled=True):

                class EventService(UpnpServerService):
                    """Rendering Control service."""

                    SERVICE_DEFINITION = ServiceInfo(
                        service_id="urn:Belkin:serviceId:basicevent1",
                        service_type="urn:Belkin:service:basicevent:1",
                        control_url="/upnp/control/basicevent1",
                        event_sub_url="/upnp/event/basicevent1",
                        scpd_url="/eventservice.xml",
                        xml=ET.Element("server_service"),
                    )

                    STATE_VARIABLE_DEFINITIONS = {
                        "BinaryState": EventableStateVariableTypeInfo(
                            data_type="boolean",
                            data_type_mapping=STATE_VARIABLE_TYPE_MAPPING["boolean"],
                            default_value="0",
                            allowed_value_range={},
                            max_rate=0,  # seconds
                            allowed_values=[
                                "0",
                                "1",
                            ],
                            xml=ET.Element("server_stateVariable"),
                        ),
                        "VETTI_ID": StateVariableTypeInfo(
                            data_type="string",
                            data_type_mapping=STATE_VARIABLE_TYPE_MAPPING["string"],
                            default_value=str(central.vetti_id),
                            allowed_value_range={},
                            allowed_values=None,
                            xml=ET.Element("server_stateVariable"),
                        ),
                    }

                    def __init__(self, requester: UpnpRequester) -> None:
                        """Initialize."""
                        super().__init__(requester)

                    @callable_action(
                        name="GetBinaryState",
                        in_args={
                            "BinaryState": "BinaryState",
                        },
                        out_args={
                            "BinaryState": "BinaryState",
                        },
                    )
                    async def get_binary_state(
                            self, BinaryState: bool
                    ) -> Dict[str, UpnpStateVariable]:
                        """Get Binary State."""
                        # pylint: disable=invalid-name, unused-argument

                        binaryState = self.state_variable("BinaryState")
                        state = await sync_to_async(top_self.get_state)(self.state_variable("VETTI_ID").value)
                        if binaryState.value != state:
                            binaryState.value = state
                        return {
                            "BinaryState": binaryState,
                        }

                    @callable_action(
                        name="SetBinaryState",
                        in_args={
                            "BinaryState": "BinaryState",
                        },
                        out_args={},
                    )
                    async def set_binary_state(
                            self, BinaryState: bool
                    ) -> Dict[str, UpnpStateVariable]:
                        """Set Binary State."""
                        # pylint: disable=invalid-name, unused-argument
                        binaryState = self.state_variable("BinaryState")
                        binaryState.value = BinaryState

                        await sync_to_async(top_self.set_state)(self.state_variable("VETTI_ID").value, BinaryState)

                        LOGGER.warning(f'BinaryState changed: {BinaryState}')

                        return {}

                class AlexaVirtualDevice(UpnpServerDevice):
                    """Virtual Switch device."""

                    DEVICE_DEFINITION = DeviceInfo(
                        device_type="urn:Belkin:device:controllee:1",  # Do Not change
                        friendly_name=f"Vetti: {central.mac_addr}",
                        manufacturer="Belkin International Inc.",
                        manufacturer_url="http://www.belkin.com",
                        udn=f"uuid:Socket-1_0-{central.mac_addr}",
                        upc="123456789",
                        model_name="Socket",  # Do Not change
                        model_description="Belkin Plugin Socket 1.0",
                        model_number="1.0",
                        model_url="http://www.belkin.com/plugin",
                        serial_number=f"{str(central.vetti_id)}",
                        presentation_url=None,
                        url="/setup.xml",
                        icons=[],
                        xml=ET.Element("server_device"),
                    )

                    EMBEDDED_DEVICES: Sequence[Type[UpnpServerDevice]] = []
                    SERVICES = [EventService]

                    def __init__(self, requester: UpnpRequester, base_uri: str, boot_id: int, config_id: int) -> None:
                        """Initialize."""

                        super().__init__(
                            requester=requester,
                            base_uri=base_uri,
                            boot_id=boot_id,
                            config_id=config_id,
                        )

                interfaces = ni.interfaces()
                all_ips = [
                    ips[ni.AF_INET][0]['addr']
                    for i in interfaces
                    if i != "lo"
                        and i in conf_settings.ALEXA['interfaces']
                        and (ips := ni.ifaddresses(i)) is not None
                        and ni.AF_INET in ips
                        and len(ips[ni.AF_INET]) > 0
                        and 'addr' in ips[ni.AF_INET][0]
                ]
                boot_id = int(time())
                for ip in all_ips:
                    logger.info(f'Starting SSDP server to {str(central.vetti_id)} at {ip}')
                    server = UpnpServer(AlexaVirtualDevice, (ip, 0),
                                        http_port=HTTP_PORT, boot_id=boot_id, config_id=1)

                    asyncio.run(self.async_main(server))

            try:
                asyncio.run(self.async_wait())
            except KeyboardInterrupt:
                pass

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error = traceback.format_exception(exc_type, exc_value, exc_traceback)
            err_txt = '%s\n\n' % exc_value
            for e in error:
                err_txt += str(e.strip('\n'))

            logger.error(err_txt)

