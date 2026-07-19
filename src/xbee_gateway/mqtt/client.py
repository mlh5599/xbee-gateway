"""MQTT client boundary.

`MqttPort` is a Protocol so tests can substitute a fake without a real broker — this is
the direct fix for the legacy gateway's module-level `client = mqtt.Client()` global,
which is what made its tests resort to patching `MQTTHelper.client.publish`.
"""
from __future__ import annotations

import threading
from typing import Protocol

from xbee_gateway.config.schema import MqttConfig


class MqttPort(Protocol):
    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def publish(self, topic: str, payload, qos: int = 0, retain: bool = False) -> None: ...

    def publish_availability(self, online: bool) -> None: ...


class PahoMqttClient:
    """Real MqttPort implementation, wrapping paho-mqtt."""

    def __init__(self, config: MqttConfig):
        import paho.mqtt.client as paho

        self._config = config
        self._client = paho.Client(client_id=config.client_id)
        if config.username:
            self._client.username_pw_set(config.username, config.password)
        if config.tls:
            self._client.tls_set()

        # LWT must be set before connect() so the broker publishes it on ungraceful disconnect.
        self._client.will_set(config.availability_topic, payload="offline", qos=1, retain=True)

        # on_connect fires on every successful connect, including paho's automatic
        # reconnects after a dropped session -- not just the initial startup connect.
        # That's what makes this the right place for the birth message, unlike a
        # one-time publish after connect() which only covers process startup.
        self._client.on_connect = self._on_connect

        self._reassert_stop = threading.Event()
        self._reassert_thread: threading.Thread | None = None

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self.publish_availability(online=True)

    def _reassert_loop(self) -> None:
        interval = self._config.availability_reassert_interval
        while not self._reassert_stop.wait(interval):
            if self._client.is_connected():
                self.publish_availability(online=True)

    def connect(self) -> None:
        self._client.connect(self._config.host, self._config.port, keepalive=60)
        self._client.loop_start()

        if self._config.availability_reassert_interval > 0:
            self._reassert_stop.clear()
            self._reassert_thread = threading.Thread(
                target=self._reassert_loop, name="mqtt-availability-reassert", daemon=True
            )
            self._reassert_thread.start()

    def disconnect(self) -> None:
        self._reassert_stop.set()
        if self._reassert_thread is not None:
            self._reassert_thread.join(timeout=5)
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload, qos: int = 0, retain: bool = False) -> None:
        self._client.publish(topic, payload, qos=qos, retain=retain)

    def publish_availability(self, online: bool) -> None:
        self.publish(
            self._config.availability_topic,
            "online" if online else "offline",
            qos=1,
            retain=True,
        )
