# Migrating From an Existing Legacy Deployment

If you have an older XBee-to-MQTT gateway (e.g. a hand-rolled script or an earlier version
of this project) already running and publishing to Home Assistant, follow this sequence to
avoid disrupting live entities during cutover.

1. **Run side by side.** Deploy `xbee-gateway` alongside the existing service, but point it
   at different `mqtt.base_topic` / `mqtt.discovery_prefix` values (e.g.
   `xbeegateway-new`, `homeassistant-new`) so it doesn't collide with entities the old
   service already created in Home Assistant. Confirm sensor readings match.
2. **Cut over.** Once verified, stop and disable the old service, freeing the serial port
   it held on the XBee coordinator. Reconfigure `xbee-gateway` back to the real topics
   (`xbeegateway`, `homeassistant`) and restart it.
3. **Clean up stale entities.** If any channel changes Home Assistant component type as
   part of migrating (for example, a raw analog value that used to be incorrectly
   published as a `binary_sensor` and is now correctly a `sensor`), Home Assistant will
   not automatically migrate the old entity — the domain itself changes. Manually remove
   the stale entity in Home Assistant's entity registry after confirming the new one is
   working.
4. **Retire the old deployment.** Once the cutover has been stable for a while, decommission
   the old service/codebase. Prefer archiving over deleting if you might want to reference
   it later.
