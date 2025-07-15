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
                        response = data.decode('utf-8', errors='replace')
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
            # Try parsing as comma-separated ASCII string (for compatibility)
            ascii_response = value_list.decode('utf-8', errors='replace')
            _LOGGER.debug(f"ASCII response: {ascii_response}")
            if ',' in ascii_response:
                values = ascii_response.split(',')
                self.state = {
                    'on': int(values[30]) if len(values) > 30 and values[30].isdigit() else 0,
                    'temp': int(values[2]) if len(values) > 2 and values[2].isdigit() else None,
                    'temp_high': int(values[3]) if len(values) > 3 and values[3].isdigit() else None,
                    'grill_set_temp': int(values[6]) if len(values) > 6 and values[6].isdigit() else None,
                    'grill_set_temp_high': int(values[7]) if len(values) > 7 and values[7].isdigit() else None,
                    'probe1_temp': int(values[4]) if len(values) > 4 and values[4].isdigit() else None,
                    'probe1_temp_high': int(values[5]) if len(values) > 5 and values[5].isdigit() else None,
                    'probe1_set_temp': int(values[27]) if len(values) > 27 and values[27].isdigit() else None,
                    'probe1_set_temp_high': int(values[28]) if len(values) > 28 and values[28].isdigit() else None,
                    'probe2_temp': int(values[16]) if len(values) > 16 and values[16].isdigit() else None,
                    'probe2_temp_high': int(values[17]) if len(values) > 17 and values[17].isdigit() else None,
                    'probe2_set_temp': int(values[18]) if len(values) > 18 and values[18].isdigit() else None,
                    'probe2_set_temp_high': int(values[19]) if len(values) > 19 and values[19].isdigit() else None,
                    'fireState': int(values[31]) if len(values) > 31 and values[31].isdigit() else None,
                    'fireStatePercentage': int(values[32]) if len(values) > 32 and values[32].isdigit() else None,
                    'warnState': int(values[23]) if len(values) > 23 and values[23].isdigit() else None
                }
            else:
                # Parse as binary response
                self.state = {
                    'on': value_list[3] if len(value_list) > 3 else 0,  # Byte 3: 0x00 (off)
                    'temp': int.from_bytes(value_list[10:12], 'big') if len(value_list) > 11 else None,  # Bytes 10-11
                    'temp_high': int.from_bytes(value_list[12:14], 'big') if len(value_list) > 13 else None,  # Bytes 12-13
                    'grill_set_temp': int.from_bytes(value_list[16:18], 'big') if len(value_list) > 17 else None,  # Bytes 16-17
                    'grill_set_temp_high': int.from_bytes(value_list[18:20], 'big') if len(value_list) > 19 else None,  # Bytes 18-19
                    'probe1_temp': int.from_bytes(value_list[20:22], 'big') if len(value_list) > 21 else None,  # Bytes 20-21
                    'probe1_temp_high': int.from_bytes(value_list[22:24], 'big') if len(value_list) > 23 else None,  # Bytes 22-23
                    'probe1_set_temp': int.from_bytes(value_list[24:26], 'big') if len(value_list) > 25 else None,  # Bytes 24-25
                    'probe1_set_temp_high': int.from_bytes(value_list[26:28], 'big') if len(value_list) > 27 else None,  # Bytes 26-27
                    'probe2_temp': int.from_bytes(value_list[28:30], 'big') if len(value_list) > 29 else None,  # Bytes 28-29
                    'probe2_temp_high': int.from_bytes(value_list[30:32], 'big') if len(value_list) > 31 else None,  # Bytes 30-31
                    'probe2_set_temp': int.from_bytes(value_list[32:34], 'big') if len(value_list) > 33 else None,  # Bytes 32-33
                    'probe2_set_temp_high': int.from_bytes(value_list[34:36], 'big') if len(value_list) > 35 else None,  # Bytes 34-35
                    'fireState': value_list[36] if len(value_list) > 36 else None,  # Byte 36
                    'fireStatePercentage': value_list[37] if len(value_list) > 37 else None,  # Byte 37
                    'warnState': value_list[38] if len(value_list) > 38 else None  # Byte 38
                }
                # Validate temperatures
                for key in ['temp', 'grill_set_temp', 'probe1_temp', 'probe2_temp']:
                    if self.state[key] is not None:
                        if self.state[key] < 0 or self.state[key] > 1000:
                            _LOGGER.warning(f"Invalid {key}: {self.state[key]}, setting to None")
                            self.state[key] = None
                        elif key in ['probe1_temp', 'probe2_temp'] and self.state[key] < self.MIN_TEMP_F_PROBE:
                            _LOGGER.debug(f"Probe {key} unplugged or ambient: {self.state[key]}, setting to None")
                            self.state[key] = None
                        elif key == 'temp' and not self.state['on'] and self.state[key] > 100:
                            _LOGGER.debug(f"Grill off, invalid temp {self.state[key]}, setting to None")
                            self.state[key] = None
            _LOGGER.debug(f"Parsed status response: {self.state}")
        except Exception as e:
            _LOGGER.error(f"Error processing status response: {e}, raw data: {value_list}")
            self.state = {'on': 0, 'temp': None, 'grill_set_temp': None, 'probe1_temp': None, 'probe2_temp': None}
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
        while status is None and count < 10:
            status = await self.send(self.CODE_STATUS)
            count += 1
            _LOGGER.debug("Status attempt %d: %s (hex: %s)", count, status, binascii.hexlify(status) if status else None)
        if status is None:
            _LOGGER.error("No response from grill at %s after %d attempts", self._ip, count)
            raise RuntimeError("No response from grill")
        _LOGGER.debug("Raw status data before parsing: %s", status)
        try:
            return await self.gmg_status_response(status)
        except Exception as e:
            _LOGGER.error(f"Error parsing status data: {e}")
            return {'on': 0, 'temp': None, 'grill_set_temp': None, 'probe1_temp': None, 'probe2_temp': None}

    async def serial(self):
        """Get serial number of grill."""
        serial = await self.send(self.CODE_SERIAL)
        if serial:
            self._serial_number = serial.decode('utf-8', errors='replace')
            _LOGGER.debug("Received serial number: %s", self._serial_number)
        else:
            _LOGGER.error("No serial number response from grill at %s", self._ip)
        return self._serial_number

    async def send(self, message, timeout=10):
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
