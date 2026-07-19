import time

from xbee_gateway.config.schema import MqttConfig
from xbee_gateway.mqtt.client import PahoMqttClient


def _client(monkeypatch, **config_overrides):
    config = MqttConfig(host="broker.local", availability_topic="xbeegateway/status", **config_overrides)
    client = PahoMqttClient(config)

    published = []
    monkeypatch.setattr(
        client._client,
        "publish",
        lambda topic, payload, qos=0, retain=False: published.append((topic, payload, qos, retain)),
    )
    # No real broker in unit tests: stub out the network calls connect()/disconnect() make.
    monkeypatch.setattr(client._client, "connect", lambda *a, **kw: None)
    monkeypatch.setattr(client._client, "loop_start", lambda: None)
    monkeypatch.setattr(client._client, "loop_stop", lambda: None)
    monkeypatch.setattr(client._client, "disconnect", lambda: None)
    monkeypatch.setattr(client._client, "is_connected", lambda: True)
    return client, published


def test_on_connect_republishes_birth_message(monkeypatch):
    """Regression test for #26: on_connect must fire the birth message every time it
    runs, not just once at startup -- paho invokes it again on automatic reconnect
    after a dropped broker session, which is exactly when the stale LWT 'offline'
    needs to be overwritten."""
    client, published = _client(monkeypatch)

    client._on_connect(client._client, None, {}, 0)
    client._on_connect(client._client, None, {}, 0)  # simulates a later auto-reconnect

    assert published == [
        ("xbeegateway/status", "online", 1, True),
        ("xbeegateway/status", "online", 1, True),
    ]


def test_on_connect_does_not_publish_on_failed_connect(monkeypatch):
    client, published = _client(monkeypatch)

    client._on_connect(client._client, None, {}, 5)  # e.g. CONNACK "not authorized"

    assert published == []


def test_periodic_reassert_republishes_while_connected(monkeypatch):
    """Belt-and-suspenders safeguard for #26: even without a reconnect event, the
    retained 'online' value should be periodically re-asserted in case it gets
    clobbered by something other than our own on_connect (e.g. broker losing retained
    state)."""
    client, published = _client(monkeypatch, availability_reassert_interval=0.02)

    client.connect()
    time.sleep(0.11)  # ~5 reassert cycles at a 20ms interval
    client.disconnect()

    assert len(published) >= 3
    assert all(entry == ("xbeegateway/status", "online", 1, True) for entry in published)


def test_periodic_reassert_disabled_when_interval_is_zero(monkeypatch):
    client, published = _client(monkeypatch, availability_reassert_interval=0)

    client.connect()
    time.sleep(0.05)
    client.disconnect()

    assert published == []


def test_periodic_reassert_skips_publish_while_disconnected(monkeypatch):
    client, published = _client(monkeypatch, availability_reassert_interval=0.02)
    monkeypatch.setattr(client._client, "is_connected", lambda: False)

    client.connect()
    time.sleep(0.05)
    client.disconnect()

    assert published == []
