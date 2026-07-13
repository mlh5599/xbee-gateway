# Milestone 3: ESPHome Smart End Device — Open Questions

This is a roadmap document, not a spec. Milestone 3 is the furthest out and most likely to
change; nothing here should be treated as decided.

## Goal

A more capable end device, built around a microcontroller, capable of two-way
communication (not just relaying sensor readings one-way like the simple XBee end
devices Milestone 1 targets). Runs actual **ESPHome firmware in MQTT mode** — i.e.
configured with ESPHome's built-in `mqtt:` component and `mqtt.discovery: true`, not the
native ESPHome API (`api:`), so it stays consistent with the rest of this project's
MQTT-everywhere design and shows up in Home Assistant via the same MQTT discovery
mechanism the Pi-side gateway uses.

## Open questions

1. **Radio**: does the device keep an XBee3 module (UART-attached to the microcontroller,
   joins the existing Zigbee mesh, and the Pi-side gateway keeps relaying it as just
   another `RemoteDevice`) — or does it go MQTT-native over WiFi directly, skipping XBee
   entirely? The latter may be more sensible once the device needs WiFi and is likely
   mains-powered anyway, which undercuts XBee's main advantages (mesh range, low power).
2. **Firmware approach**: a custom ESPHome `external_components/` package implementing a
   UART transport for XBee API frames, exposing sensor pins as ESPHome `sensor` /
   `binary_sensor` / `switch` / `number` platforms — *if* the XBee-attached option is
   chosen.
3. **Topic scheme**: should the device's MQTT topics match the gateway's
   (`xbeegateway/<address>/<channel>/...`), or just use ESPHome's own default topic
   scheme, since either way it's discovered independently via MQTT discovery?
4. **Hardware**: ESP32 vs ESP32-C3/C6 vs ESP8266; power budget and enclosure are
   undecided.
5. **Repo location**: recommend a separate repo (e.g. `xbee-smart-node-firmware`) when
   this milestone actually starts — ESPHome's YAML/`external_components`/build tooling
   doesn't fit naturally alongside this repo's Python packaging. A monorepo `firmware/`
   subdirectory remains an option if that's preferred later; no cost is paid by deferring
   the decision.

Resolve these via a design spike (see the Milestone 3 issues) before any implementation
work starts.
