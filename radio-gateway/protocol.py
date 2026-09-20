"""
AbhaySetu radio gateway firmware contract (ESP32 / LoRa-compatible module).

This sketch is a transport, not a commercial radio product integration.
Wire your LoRa module using the vendor's library and keep framing identical.

Framing:
  MAGIC(3) = 'ABS'
  VERSION(1)
  LENGTH(2, big-endian)
  PAYLOAD(length)
  CRC16(2)

The gateway must only report TX_OK after the radio stack confirms airtime,
and ACK only after the remote gateway confirms receipt.
"""

# This file documents the serial/BLE contract used by RadioAdapter.
PROTOCOL_MAGIC = b"ABS"
PROTOCOL_VERSION = 1
CMD_SEND = 0x01
CMD_ACK = 0x02
CMD_NACK = 0x03
CMD_STATUS = 0x04
