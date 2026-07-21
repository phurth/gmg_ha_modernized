"""Green Mountain Grill API library"""
import socket
import binascii
import ipaddress
import logging

from .const import STATUS_RETRIES, STATUS_TIMEOUT

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
        """Parse a binary status ('UR') frame from the grill.

        Temperatures are little-endian 16-bit values (low byte, then high
        byte). Byte offsets follow the established GMG UDP protocol.
        """
        _LOGGER.debug(
            "Raw status: len=%d hex=%s",
            len(value_list), binascii.hexlify(bytearray(value_list)),
        )

        def u16(low):
            """Return the little-endian 16-bit value at byte offset `low`."""
            if len(value_list) > low + 1:
                return value_list[low] + (value_list[low + 1] << 8)
            return None

        try:
            self.state = {
                'on': value_list[30] if len(value_list) > 30 else 0,
                'temp': u16(2),
                'grill_set_temp': u16(6),
                'probe1_temp': u16(4),
                'probe1_set_temp': u16(28),
                'probe2_temp': u16(16),
                'probe2_set_temp': u16(18),
                'fireState': value_list[32] if len(value_list) > 32 else None,
                'fireStatePercentage': value_list[33] if len(value_list) > 33 else None,
                'warnState': value_list[24] if len(value_list) > 24 else None,
            }
            # An unplugged probe reads out of range; report it as unknown.
            for key in ('probe1_temp', 'probe2_temp'):
                val = self.state[key]
                if val is None or val <= self.MIN_TEMP_F_PROBE or val > self.MAX_TEMP_F_PROBE:
                    self.state[key] = None
            _LOGGER.debug("Parsed status: %s", self.state)
        except Exception as e:
            _LOGGER.error("Error processing status response: %s, raw=%s", e, value_list)
            self.state = {'on': 0, 'temp': None, 'grill_set_temp': None,
                          'probe1_temp': None, 'probe2_temp': None}
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

    async def status(self, retries=STATUS_RETRIES, timeout=STATUS_TIMEOUT):
        """Poll the grill for status.

        Retries a few times to ride out transient UDP drops, but fails fast
        (short timeout, few attempts) so an unplugged grill doesn't stall the
        caller. Raises RuntimeError when the grill can't be reached.
        """
        _LOGGER.debug("Requesting status from grill at %s", self._ip)
        raw = None
        for attempt in range(1, retries + 1):
            raw = await self.send(self.CODE_STATUS, timeout=timeout)
            if raw is not None:
                break
            _LOGGER.debug("Status attempt %d/%d: no response from %s", attempt, retries, self._ip)
        if raw is None:
            raise RuntimeError(f"No response from grill at {self._ip}")
        return await self.gmg_status_response(raw)

    async def serial(self, timeout=STATUS_TIMEOUT):
        """Fetch and cache the grill's serial number. Returns '' if unreachable."""
        serial = await self.send(self.CODE_SERIAL, timeout=timeout)
        if serial:
            self._serial_number = serial.decode('utf-8', errors='replace').strip()
            _LOGGER.debug("Received serial number: %s", self._serial_number)
        else:
            _LOGGER.warning("No serial number response from grill at %s", self._ip)
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
