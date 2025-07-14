"""Green Mountain Grill API library"""
import socket
import binascii
import ipaddress
import logging

_LOGGER = logging.getLogger(__name__)

def grills(hass, timeout=1, ip_bind_address='0.0.0.0'):
    """Discover GMG grills on the network."""
    _LOGGER.debug("Opening up UDP sockets and broadcasting for grills.")

    interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
    allips = [ip[-1][0] for ip in interfaces]
    allips.append(ip_bind_address)

    grills = []
    message = grill.CODE_SERIAL

    for ip in allips:
        _LOGGER.debug(f"Creating socket for IP: {ip}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((ip, 0))
            sock.settimeout(timeout)

            # Run blocking socket operations in executor
            def send_broadcast():
                sock.sendto(message, ('<broadcast>', grill.UDP_PORT))
                _LOGGER.debug("Broadcast sent.")
                responses = []
                while True:
                    try:
                        data, (address, ret_socket) = sock.recvfrom(1024)
                        response = data.decode('utf-8')
                        responses.append((response, address, ret_socket))
                    except socket.timeout:
                        break
                return responses

            responses = hass.loop.run_in_executor(None, send_broadcast)

            for response, address, ret_socket in responses:
                _LOGGER.debug(f"Received a response {address}:{ret_socket}, {response}")
                add_grill = True
                if response.startswith('GMG'):
                    _LOGGER.debug(f"Found grill {address}:{ret_socket}, {response}")
                    for grill_test in grills:
                        if grill_test._serial_number == response:
                            _LOGGER.debug(f"Grill {response} is a duplicate. Not adding to collection.")
                            add_grill = False
                    if add_grill:
                        grills.append(grill(hass, address, response))

        except Exception as e:
            _LOGGER.error(f"Error discovering grills on {ip}: {e}")
        finally:
            sock.close()

    _LOGGER.debug(f"Found {len(grills)} grills.")
    return grills

class grill:
    UDP_PORT = 8080
    MIN_TEMP_F = 150
    MAX_TEMP_F = 500
    MIN_TEMP_F_PROBE = 32
    MAX_TEMP_F_PROBE = 257
    CODE_SERIAL = b'UL!'
    CODE_STATUS = b'UR001!'

    def __init__(self, hass, ip, serial_number=''):
        if not ipaddress.ip_address(ip):
            raise ValueError(f"IP address not valid {ip}")
        _LOGGER.debug(f"Initializing grill {ip} with serial number {serial_number}")
        self.hass = hass
        self._ip = ip
        self._serial_number = serial_number
        self.state = {}

    async def gmg_status_response(self, value_list):
        """Process status response from grill."""
        _LOGGER.debug(f"Status response raw: {value_list}")
        try:
            self.state['on'] = value_list[30]
            self.state['temp'] = value_list[2]
            self.state['temp_high'] = value_list[3]
            self.state['grill_set_temp'] = value_list[6]
            self.state['grill_set_temp_high'] = value_list[7]
            self.state['probe1_temp'] = value_list[4]
            self.state['probe1_temp_high'] = value_list[5]
            self.state['probe1_set_temp'] = value_list[28]
            self.state['probe1_set_temp_high'] = value_list[29]
            self.state['probe2_temp'] = value_list[16]
            self.state['probe2_temp_high'] = value_list[17]
            self.state['probe2_set_temp'] = value_list[18]
            self.state['probe2_set_temp_high'] = value_list[19]
            self.state['fireState'] = value_list[32]
            self.state['fireStatePercentage'] = value_list[33]
            self.state['warnState'] = value_list[24]
        except Exception as e:
            _LOGGER.error(f"Error processing status: {e}")
        _LOGGER.debug(f"Status response: {self.state}")
        return self.state

    async def set_temp(self, target_temp):
        """Set the target temperature for the grill."""
        if target_temp < self.MIN_TEMP_F or target_temp > self.MAX_TEMP_F:
            raise ValueError(f"Target temperature {target_temp} is out of range")
        message = b'UT' + str(target_temp).encode() + b'!'
        return await self.send(message)

    async def set_temp_probe(self, target_temp, probe_number):
        """Set the target temperature for the grill probe."""
        if target_temp < self.MIN_TEMP_F_PROBE or target_temp > self.MAX_TEMP_F_PROBE:
            raise ValueError(f"Target temperature {target_temp} is out of range")
        if probe_number == 1:
            message = b'UF' + str(target_temp).encode() + b'!'
        elif probe_number == 2:
            message = b'Uf' + str(target_temp).encode() + b'!'
        else:
            raise ValueError(f"Invalid probe number: {probe_number}")
        return await self.send(message)

    async def power_on_cool(self):
        """Power on the grill to cold smoke mode."""
        message = b'UK002!'
        return await self.send(message)

    async def power_on(self):
        """Power on the grill."""
        message = b'UK001!'
        return await self.send(message)

    async def power_off(self):
        """Power off the grill."""
        message = b'UK004!'
        return await self.send(message)

    async def status(self):
        """Get status of grill."""
        status = None
        count = 0
        while status is None and count < 5:
            status = await self.send(self.CODE_STATUS)
            count += 1
        if status is None:
            raise RuntimeError("No response from grill")
        return await self.gmg_status_response(list(status))

    async def serial(self):
        """Get serial number of grill."""
        self._serial_number = (await self.send(self.CODE_SERIAL)).decode('utf-8')
        return self._serial_number

    async def send(self, message, timeout=1):
        """Send messages via UDP to grill asynchronously."""
        def send_blocking():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.settimeout(timeout)
                sock.sendto(message, (self._ip, self.UDP_PORT))
                data, _ = sock.recvfrom(1024)
                return data
            except socket.timeout:
                _LOGGER.debug("Socket timeout")
                return None
            except Exception as e:
                _LOGGER.error(f"Error sending message: {e}")
                return None
            finally:
                sock.close()

        return await self.hass.async_add_executor_job(send_blocking)
