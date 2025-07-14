"""Green Mountain Grill API library"""
import socket
import binascii
import ipaddress
import logging

_LOGGER = logging.getLogger(__name__)

def grills(hass, timeout=1, ip_bind_address='0.0.0.0'):
    """Discover GMG grills on the network."""
    _LOGGER.debug("Opening UDP sockets and broadcasting for grills.")
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

            def send_broadcast():
                sock.sendto(message, ('<broadcast>', grill.UDP_PORT))
                _LOGGER.debug("Broadcast sent on %s", ip)
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
                _LOGGER.debug(f"Received discovery response from {address}:{ret_socket}: {response}")
                add_grill = True
                if response.startswith('GMG'):
                    _LOGGER.debug(f"Found grill {address}:{ret_socket}, serial: {response}")
                    for grill_test in grills:
                        if grill_test._serial_number == response:
                            _LOGGER.debug(f"Grill {response} is a duplicate. Not adding.")
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
        _LOGGER.debug(f"Raw status response: {value_list}, length: {len(value_list)}, hex: {binascii.hexlify(bytearray(value_list))}")
        try:
            self.state = {
                'on': value_list[30] if len(value_list) > 30 else None,
                'temp': value_list[2] if len(value_list) > 2 else None,
                'temp_high': value_list[3] if len(value_list) > 3 else None,
                'grill_set_temp': value_list[6] if len(value_list) > 6 else None,
                'grill_set_temp_high': value_list[7] if len(value_list) > 7 else None,
                'probe1_temp': value_list[4] if len(value_list) > 4 else None,
                'probe1_temp_high': value_list[5] if len(value_list) > 5 else None,
                'probe1_set_temp': value_list[28] if len(value_list) > 28 else None,
                'probe1_set_temp_high': value_list[29] if len(value_list) > 29 else None,
                'probe2_temp': value_list[16] if len(value_list) > 16 else None,
                'probe2_temp_high': value_list[17] if len(value_list) > 17 else None,
                'probe2_set_temp': value_list[18] if len(value_list) > 18 else None,
                'probe2_set_temp_high': value_list[19] if len(value_list) > 19 else None,
                'fireState': value_list[32] if len(value_list) > 32 else None,
                'fireStatePercentage': value_list[33] if len(value_list) > 33 else None,
                'warnState': value_list[24] if len(value_list) > 24 else None
            }
            _LOGGER.debug(f"Parsed status response: {self.state}")
        except Exception as e:
            _LOGGER.error(f"Error processing status response: {e}")
            self.state = {}
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
        _LOGGER.debug("Requesting status from grill at %s", self._ip)
        status = None
        count = 0
        while status is None and count < 5:
            status = await self.send(self.CODE_STATUS)
            count += 1
            _LOGGER.debug("Status attempt %d: %s (hex: %s)", count, status, binascii.hexlify(status) if status else None)
        if status is None:
            _LOGGER.error("No response from grill at %s after %d attempts", self._ip, count)
            raise RuntimeError("No response from grill")
        _LOGGER.debug("Raw status data before parsing: %s", status)
        try:
            value_list = list(status)
            return await self.gmg_status_response(value_list)
        except Exception as e:
            _LOGGER.error("Error parsing status data: %s", e)
            return {}

    async def serial(self):
        """Get serial number of grill."""
        serial = await self.send(self.CODE_SERIAL)
        if serial:
            self._serial_number = serial.decode('utf-8')
            _LOGGER.debug("Received serial number: %s", self._serial_number)
        else:
            _LOGGER.error("No serial number response from grill at %s", self._ip)
        return self._serial_number

    async def send(self, message, timeout=3):
        """Send messages via UDP to grill asynchronously."""
        _LOGGER.debug("Sending message to %s:%d: %s", self._ip, self.UDP_PORT, message)
        def send_blocking():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.settimeout(timeout)
                sock.sendto(message, (self._ip, self.UDP_PORT))
                data, addr = sock.recvfrom(1024)
                _LOGGER.debug("Received response from %s: %s (hex: %s)", addr, data, binascii.hexlify(data))
                return data
            except socket.timeout:
                _LOGGER.debug("Socket timeout for %s:%d", self._ip, self.UDP_PORT)
                return None
            except Exception as e:
                _LOGGER.error("Error sending message to %s:%d: %s", self._ip, self.UDP_PORT, e)
                return None
            finally:
                sock.close()

        return await self.hass.async_add_executor_job(send_blocking)
