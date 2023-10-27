import json, requests
import logging
import socket, re
from time import sleep
import netifaces as ni

import datetime, sys, traceback, os
from typing import Optional

from django.conf import settings as conf_settings

from manager.dbmodels.vetti import Vetti
from tools import Tools

logger = logging.getLogger('Vetti Searcher')
logger.setLevel(logging.DEBUG)
if os.isatty(0):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
else:
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    logger.addHandler(handler)

requests.packages.urllib3.disable_warnings()


class SearchVetti():
    log_source = "Vetti Searcher"
    UDP_PORT = 5000

    def __init__(self):
        pass

    def process(self):
        logger.info("Vetti Searcher")

        pid = str(os.getpid())
        pidfile = "/tmp/search_vetti.pid"

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
            self.do_check_vetti()

            for central in Vetti.objects.filter(enabled=True):
                self.do_check_status(central)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error = traceback.format_exception(exc_type, exc_value, exc_traceback)
            err_txt = '%s\n\n' % exc_value
            for e in error:
                err_txt += str(e.strip('\n'))

            logger.error(err_txt)
        finally:
            os.unlink(pidfile)

    def do_check_status(self, vetti: Vetti):
        AUTH = f"[T128 TEC Idx=401 Cmd=3 Par={conf_settings.VETTI['config_password']}]"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP

        sock.sendto(AUTH.encode(), (vetti.ip_addr, SearchVetti.UDP_PORT))
        sock.recvfrom(1024)

        # get actual status
        sock.sendto(f"[T137 CMD 2]".encode(), (vetti.ip_addr, SearchVetti.UDP_PORT))
        data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes

        if isinstance(data, bytes):
            data = data.decode("UTF-8")

        m = re.search(r'\[R137.*p:([SAN-])', data, re.IGNORECASE)
        if m is None:
            return

        st = m.group(1).upper()

        if st in ("S", "A") and vetti.armed:
            return

        if st == "-" and vetti.armed:
            vetti.armed = False
            vetti.save()
            Tools.send_telegram(text=(f"Alarme desligado via controle: \n"
                                      f"MAC:{vetti.mac_display}\n"
                                      f"IP:{vetti.ip_addr}\n"
                                      f"Name:{vetti.name}\n"))
            return

        if st in ("S", "A") and not vetti.armed:
            name = "stay" if st == "S" else "full"
            vetti.armed = True
            vetti.save()
            Tools.send_telegram(text=(f"Alarme acionado {name} via controle: \n"
                                      f"MAC:{vetti.mac_display}\n"
                                      f"IP:{vetti.ip_addr}\n"
                                      f"Name:{vetti.name}\n"))
            return

    def do_check_vetti(self):
        for vetti in SearchVetti.search_vetti():
            try:
                central = Vetti.objects.filter(enabled=True, mac_addr=vetti['mac'].lower().replace("-", "")).first()
                if central is None:
                    Vetti.objects.create(
                        mac_addr=vetti['mac'],
                        name=vetti['name'],
                        ip_addr=vetti['ip'],
                    )
                    Tools.send_telegram(text=(f"New Vetti central found: \n"
                                              f"MAC:{vetti['mac']}\n"
                                              f"IP:{vetti['ip']}\n"
                                              f"Name:{vetti['name']}\n"))
                else:
                    # to update last search
                    save = central.updated <= datetime.datetime.now() - datetime.timedelta(minutes=5)

                    if central.ip_addr != vetti['ip']:
                        central.ip_addr = vetti['ip']
                        save = True

                    if central.name != vetti['name']:
                        central.name = vetti['name']
                        save = True

                    if save:
                        central.save()
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error = traceback.format_exception(exc_type, exc_value, exc_traceback)
                err_txt = '%s\n\n' % exc_value
                for e in error:
                    err_txt += str(e.strip('\n'))

                logger.error(err_txt)

    @staticmethod
    def update_state(vetti: Vetti):

        AUTH = f"[T128 TEC Idx=401 Cmd=3 Par={conf_settings.VETTI['config_password']}]"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP

        sock.sendto(AUTH.encode(), (vetti.ip_addr, SearchVetti.UDP_PORT))
        sock.recvfrom(1024)

        if vetti.armed:
            sock.sendto(f"[T134 CMDX Id=25 User={conf_settings.VETTI['user_password']} Part=100000]".encode(),
                        (vetti.ip_addr, SearchVetti.UDP_PORT))

            Tools.send_telegram(text=(f"Alarme acionado stay via alexa: \n"
                                      f"MAC:{vetti.mac_display}\n"
                                      f"IP:{vetti.ip_addr}\n"
                                      f"Name:{vetti.name}\n"))
        else:
            sock.sendto(f"[T146 CMDX Id=22 User={conf_settings.VETTI['user_password']} Part=100000]".encode(),
                        (vetti.ip_addr, SearchVetti.UDP_PORT))

            Tools.send_telegram(text=(f"Alarme desligado via alexa: \n"
                                      f"MAC:{vetti.mac_display}\n"
                                      f"IP:{vetti.ip_addr}\n"
                                      f"Name:{vetti.name}\n"))

    @staticmethod
    def search_vetti() -> list[dict]:
        SEARCH = b"[T001 ID]"

        interfaces = ni.interfaces()
        allips = [
            ips[ni.AF_INET][0]['addr']
            for i in interfaces
            if i != "lo"
               and (ips := ni.ifaddresses(i)) is not None
               and ni.AF_INET in ips
               and len(ips[ni.AF_INET]) > 0
               and 'addr' in ips[ni.AF_INET][0]
        ]

        for _ in range(60):
            found = False
            for ip in allips:
                #logger.debug(f"Checking {ip}")
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(0.2)
                sock.bind((ip, SearchVetti.UDP_PORT))
                sock.sendto(SEARCH, ('255.255.255.255', SearchVetti.UDP_PORT))
                try:
                    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

                    if isinstance(data, bytes):
                        data = data.decode("UTF-8")

                    #logger.debug(f"Message received from {addr}: {data}")

                    m = re.search("\[R001.*Mac:([a-fA-F0-9\-]+).*IP:([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}).*Nome:[ \"]{0,2}([^\"]+)", data, re.IGNORECASE)
                    if m:
                        found = True
                        yield dict(name=m.group(3).strip(), ip=m.group(2), mac=m.group(1))
                    else:
                        logger.error("received unknown message: %s" % data)

                except socket.timeout:
                    pass
                sock.close()

            if found:
                break

            sleep(0.3)
