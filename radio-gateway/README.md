# Radio / LoRa gateway

AbhaySetu talks to radio hardware through `RadioAdapter`:

- `discoverGateway()`
- `connectGateway()`
- `sendMessage()` / `receiveMessage()`
- `getSignalStatus()` / `getBatteryStatus()`
- `disconnectGateway()`

## What this is

A hardware abstraction and an ESP32 sketch that frames SOS payloads. It is **not** a partnership with a commercial radio network and does **not** dispatch police, fire, or ambulance services.

## What you need

1. ESP32 (or equivalent) plus a LoRa-compatible module.
2. A remote gateway that understands the same `ABS` frame format.
3. That remote gateway connected to an AbhaySetu local hub or the cloud backend.

Until a gateway is discovered and it confirms transmission, the app shows radio as unavailable and will not claim radio delivery.

## Protocol

See `protocol.py` and `abhaysetu_gateway.ino`. Replace `lora_transmit()` with your module driver. Return success only when the radio stack confirms the frame was sent.
