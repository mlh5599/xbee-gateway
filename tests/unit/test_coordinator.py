import pytest

from xbee_gateway.config.schema import ATSetting, CoordinatorConfig
from xbee_gateway.xbee.coordinator import CoordinatorService


def _config(**overrides):
    defaults = dict(
        serial_port="/dev/ttyUSB0",
        baud_rate=9600,
        reset_gpio_pin=-1,
        status_led_gpio_pin=-1,
        gpio_backend="none",
        connect_retry_attempts=3,
        connect_retry_backoff_seconds=0,
        at_settings={},
    )
    defaults.update(overrides)
    return CoordinatorConfig(**defaults)


def test_apply_at_settings_writes_new_value(fake_radio, fake_gpio):
    config = _config(at_settings={"pan_id": ATSetting(at="ID", value="0x2000")})
    service = CoordinatorService(fake_radio, config, fake_gpio)

    service.initialize()

    assert fake_radio.set_calls == [("ID", bytes.fromhex("2000"))]
    assert fake_radio.write_changes_called is True


def test_verify_before_write_skips_unchanged_value(fake_radio, fake_gpio):
    fake_radio.parameters["ID"] = bytes.fromhex("2000")
    config = _config(
        at_settings={"pan_id": ATSetting(at="ID", value="0x2000", verify_before_write=True)}
    )
    service = CoordinatorService(fake_radio, config, fake_gpio)

    service.initialize()

    assert fake_radio.set_calls == []
    assert fake_radio.write_changes_called is False


def test_empty_value_is_skipped(fake_radio, fake_gpio):
    config = _config(at_settings={"network_encryption_key": ATSetting(at="KY", value="")})
    service = CoordinatorService(fake_radio, config, fake_gpio)

    service.initialize()

    assert fake_radio.set_calls == []


def test_reset_gpio_pulses_when_configured(fake_radio, fake_gpio):
    config = _config(reset_gpio_pin=17)
    service = CoordinatorService(fake_radio, config, fake_gpio)

    service.initialize()

    assert fake_gpio.pulses == [17]


def test_initialize_retries_then_raises_after_exhausting_attempts(fake_gpio):
    class AlwaysFailsRadio:
        def open(self):
            raise ConnectionError("no radio")

    config = _config(connect_retry_attempts=3)
    service = CoordinatorService(AlwaysFailsRadio(), config, fake_gpio)

    with pytest.raises(RuntimeError):
        service.initialize()
