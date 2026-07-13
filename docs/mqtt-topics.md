# MQTT Topic Scheme

All topics are configurable via `mqtt.base_topic` and `mqtt.discovery_prefix` in
`config.json`; the values below use the defaults.

## Discovery (retained)

```
homeassistant/sensor/xbee-0x<address>/<channel-slug>/config
homeassistant/binary_sensor/xbee-0x<address>/<channel-slug>/config
```

Published once per channel when a device is (auto-)registered. Component (`sensor` vs
`binary_sensor`) is chosen from the channel's `kind` — see
[configuration.md](configuration.md). Every payload includes `availability_topic`,
`payload_available`, `payload_not_available` pointing at the gateway's availability topic
below, so entities correctly show unavailable when the gateway is stopped or the device
hasn't been heard from.

## State

```
xbeegateway/<address>/<channel-slug>/state
```

Published on every new reading (analog) or on debounced state change (thresholded/digital).

## Availability (retained, LWT)

```
xbeegateway/status
```

`online` published on connect, `offline` set as the MQTT Last Will and Testament (so the
broker publishes it automatically on ungraceful disconnect) and also published explicitly
on graceful shutdown.
