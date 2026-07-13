# Secondary deployment path — the primary target for low-resource hardware
# (e.g. Raspberry Pi Model B/Zero, ARMv6) is the systemd installer in deploy/scripts.
# Docker is intended for beefier hosts (Pi 4/5, x86).
FROM python:3.11-slim AS build
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim
RUN useradd --system --create-home xbeegateway
COPY --from=build /install /usr/local
COPY config /opt/xbee-gateway/config
USER xbeegateway
WORKDIR /opt/xbee-gateway

# GPIO (coordinator reset line / status LED) is not available in a standard container.
# Set coordinator.gpio_backend to "none" unless you pass through /dev/gpiomem explicitly.
ENV XBEE_GATEWAY_CONFIG=/opt/xbee-gateway/config/config.json
ENV XBEE_GATEWAY_DEVICES=/opt/xbee-gateway/config/devices.json

ENTRYPOINT ["xbee-gateway"]
