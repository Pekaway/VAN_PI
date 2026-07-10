#########################
#                       #
#       Script by       #
#      Pekaway GmbH     #
#                       #
#########################

import argparse
import asyncio
import contextlib
import json
import logging
import re
import signal
import subprocess
import sys
import uuid
from time import monotonic

from bleak import BleakClient

BLE_HARD_RESET_THRESHOLD = 3
BLE_HARD_RESET_WAIT = 5.0
MPPT_STATUS_POLL_INTERVAL = 16.0
MPPT_HISTORY_CACHE_SECONDS = 300.0


def _scrub_error_word(text):
    return re.sub(r"\berror\b", "issue", text, flags=re.IGNORECASE)


class PekawayBleMppt:
    def __init__(self, logger=None, request_timeout=10.0, notification_min_length=91, debug_mppt=False):
        self.logger = logger or logging.getLogger(__name__)
        self.client = None
        self.request_timeout = request_timeout
        self.notification_min_length = notification_min_length
        self.debug_mppt = debug_mppt
        self.connect_timeout = 15.0
        self.io_timeout = 10.0

        self.GET_STATUS_PAYLOAD = bytes.fromhex("fe043030002bab15")
        self.GET_STATUS_UUID = uuid.UUID("0000ff02-0000-1000-8000-00805f9b34fb")
        self.NOTIFY_UUID = uuid.UUID("0000ff01-0000-1000-8000-00805f9b34fb")
        self.ENABLE_UUID = uuid.UUID("0000ff03-0000-1000-8000-00805f9b34fb")

        self._buffer = bytearray()
        self._future = None
        self._disconnecting = False
        self._loop = None
        self._session_id = 0
        self._protocol_hint = None
        self._protocol_mode = None
        self._characteristics = {}
        self._characteristics_by_short = {}
        self._service_shorts = set()
        self._frames = {}
        self._notify_shorts = set()
        self._query_writer_short = None
        self._history_cache = None
        self._history_cache_at = None
        self._legacy_realtime_tick = 0
        self._modbus_capture = None
        self._service_shorts = set()

    @property
    def is_connected(self):
        return bool(self.client and self.client.is_connected)

    async def connect(self, mac_address):
        if self.is_connected:
            return

        self._session_id += 1
        session_id = self._session_id
        self.logger.info("Connecting to the Pekaway MPPT device at %s session=%s", mac_address, session_id)
        self._disconnecting = False
        self.client = BleakClient(
            mac_address,
            disconnected_callback=lambda client, sid=session_id: self._on_disconnected(client, sid),
        )

        try:
            await asyncio.wait_for(self.client.connect(), timeout=self.connect_timeout)
            if not self.client.is_connected:
                raise ConnectionError("BLE client reported a failed connection")

            await self._discover_characteristics()
            await self._start_notifications()
            await self._enable_notifications()
            self._protocol_hint = self._detect_protocol_mode()
            self.logger.info("Initial MPPT protocol hint=%s session=%s", self._protocol_hint, session_id)
            if self.debug_mppt:
                self._log_characteristic_profile()
            self.logger.info("BLE notifications enabled")
        except Exception:
            await self.disconnect()
            raise

    async def disconnect(self):
        client = self.client
        self.client = None
        self._disconnecting = True

        future = self._future
        self._future = None
        self._buffer.clear()
        self._frames.clear()
        self._notify_shorts.clear()
        self._query_writer_short = None
        self._protocol_hint = None
        self._protocol_mode = None
        self._history_cache = None
        self._history_cache_at = None
        self._legacy_realtime_tick = 0
        self._modbus_capture = None

        if future and not future.done():
            future.set_exception(ConnectionError("MPPT disconnected"))

        if not client:
            self._disconnecting = False
            return

        try:
            if client.is_connected:
                for short in sorted(self._characteristics_by_short):
                    characteristic = self._characteristics_by_short[short]
                    if not self._char_has_property(characteristic, "notify") and not self._char_has_property(
                        characteristic, "indicate"
                    ):
                        continue
                    try:
                        await asyncio.wait_for(client.stop_notify(characteristic.uuid), timeout=5.0)
                    except Exception:
                        self.logger.debug("stop_notify failed during disconnect for %s", short, exc_info=True)

                try:
                    await asyncio.wait_for(client.disconnect(), timeout=5.0)
                except Exception:
                    self.logger.debug("disconnect failed during cleanup", exc_info=True)
        finally:
            self._disconnecting = False

    async def hard_reset_bluetooth(self, mac_address):
        self.logger.warning(
            "disconnect streak exceeded threshold=%s, running bluetoothctl disconnect for %s",
            BLE_HARD_RESET_THRESHOLD,
            mac_address,
        )

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["bluetoothctl", "disconnect", mac_address],
                capture_output=True,
                text=True,
                check=False,
            )
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            detail = _scrub_error_word(stderr or stdout or f"returncode={proc.returncode}")
            if proc.returncode == 0:
                self.logger.warning(
                    "bluetoothctl disconnect sent mac=%s stdout=%s",
                    mac_address,
                    stdout or "<empty>",
                )
            else:
                self.logger.warning(
                    "bluetoothctl disconnect failed mac=%s rc=%s detail=%s",
                    mac_address,
                    proc.returncode,
                    detail,
                )
        except Exception:
            self.logger.exception("bluetoothctl disconnect failure mac=%s", mac_address)

        self.logger.warning("waiting %ss after bluetoothctl disconnect", BLE_HARD_RESET_WAIT)
        await asyncio.sleep(BLE_HARD_RESET_WAIT)

    async def get_status(self, stop_event=None, include_history=True):
        if not self.is_connected:
            raise ConnectionError("MPPT is not connected")

        mode = self._protocol_mode
        status = None
        if mode is None:
            mode, status = await self._resolve_protocol_mode(stop_event=stop_event)
            if mode is None:
                raise TimeoutError("Timed out waiting for MPPT status")

        if status is None:
            if mode == "legacy":
                status = await self._get_status_legacy(stop_event=stop_event)
                if status is None:
                    if self.debug_mppt:
                        self.logger.debug("legacy status failed, trying modern fallback")
                    status = await self._get_status_modern(stop_event=stop_event)
                    if status is not None:
                        self._protocol_mode = "modern"
            else:
                status = await self._get_status_modern(stop_event=stop_event)
                if status is None:
                    if self.debug_mppt:
                        self.logger.debug("modern status failed, trying legacy fallback")
                    status = await self._get_status_legacy(stop_event=stop_event)
                    if status is not None:
                        self._protocol_mode = "legacy"

        if status is None:
            raise TimeoutError("Timed out waiting for MPPT status")

        if include_history and status is not None:
            try:
                history_data = await self._get_history_cached(
                    stop_event=stop_event,
                    running_days=status.get("PekawayBLEMppt", {}).get("runningDays"),
                )
                if history_data:
                    status.setdefault("PekawayBLEMppt", {})["history"] = history_data
            except Exception as exc:
                self.logger.debug("History fetch failed during status cycle: %s", exc, exc_info=True)

        return status

    async def _resolve_protocol_mode(self, stop_event=None):
        hint = self._protocol_hint or self._detect_protocol_mode()
        order = [hint, "legacy" if hint == "modern" else "modern"]

        for mode in order:
            if self.debug_mppt:
                self.logger.debug("protocol probe start mode=%s hint=%s session=%s", mode, hint, self._session_id)
            started = monotonic()
            if mode == "modern":
                status = await self._get_status_modern(
                    stop_event=stop_event,
                    probe=True,
                    poll_reads_during_wait=False,
                )
            else:
                status = await self._get_status_legacy(
                    stop_event=stop_event,
                    probe=True,
                    poll_reads_during_wait=False,
                )
            elapsed_ms = int((monotonic() - started) * 1000)
            if self.debug_mppt:
                self.logger.debug(
                    "protocol probe done mode=%s elapsed_ms=%s success=%s session=%s",
                    mode,
                    elapsed_ms,
                    status is not None,
                    self._session_id,
                )

            if status is not None:
                self._protocol_mode = mode
                self.logger.info("Detected MPPT protocol mode=%s session=%s", mode, self._session_id)
                return mode, status

        return None, None

    async def get_history(self, stop_event=None, running_days=None):
        if not self.is_connected:
            raise ConnectionError("MPPT is not connected")

        history = await self._query_history_snapshot(stop_event=stop_event, running_days=running_days)
        self._history_cache = history
        self._history_cache_at = monotonic()
        return {"PekawayBLEMppt": {"history": history}}

    async def _get_history_cached(self, stop_event=None, running_days=None):
        if self._history_cache is not None and self._history_cache_at is not None:
            age = monotonic() - self._history_cache_at
            if age <= MPPT_HISTORY_CACHE_SECONDS:
                return self._history_cache

        history = await self.get_history(stop_event=stop_event, running_days=running_days)
        return history.get("PekawayBLEMppt", {}).get("history")

    def _sanitize_history_kwh_series(self, series, max_daily_kwh=100.0):
        sanitized = []
        for value in series:
            if value is None:
                sanitized.append(0.0)
                continue
            if value < 0 or value > max_daily_kwh:
                sanitized.append(0.0)
                continue
            sanitized.append(value)
        return sanitized

    def _detect_protocol_mode(self):
        # The modern units expose an extra ff10 service in the field captures.
        # Legacy units seen so far do not.
        if "ff10" in self._service_shorts:
            return "modern"

        return "legacy"

    def _log_characteristic_profile(self):
        rows = []
        service_rows = ",".join(sorted(self._service_shorts)) if self._service_shorts else "(none)"
        for short in ("ff01", "ff02", "ff03", "ff04"):
            characteristic = self._characteristics_by_short.get(short)
            if characteristic is None:
                rows.append(f"{short}: missing")
                continue
            props = sorted(self._properties(characteristic))
            rows.append(
                f"{short}: uuid={characteristic.uuid} props={','.join(props) if props else '(none)'}"
            )
        self.logger.debug("MPPT service profile: %s", service_rows)
        self.logger.debug("MPPT characteristic profile: %s", " | ".join(rows))

    async def _discover_characteristics(self):
        self._characteristics.clear()
        self._characteristics_by_short.clear()
        self._service_shorts.clear()

        services = await self.client.get_services()
        for service in services:
            self._service_shorts.add(self._short_uuid(service.uuid))
            for characteristic in service.characteristics:
                key = str(characteristic.uuid).lower()
                short = self._short_uuid(characteristic.uuid)
                self._characteristics[key] = characteristic
                if short not in self._characteristics_by_short:
                    self._characteristics_by_short[short] = characteristic

    async def _start_notifications(self):
        self._notify_shorts.clear()
        for short in ("ff01", "ff02", "ff03", "ff04"):
            characteristic = self._characteristics_by_short.get(short)
            if characteristic is None:
                continue

            can_notify = self._char_has_property(characteristic, "notify") or self._char_has_property(
                characteristic, "indicate"
            )
            if not can_notify and short not in {"ff01", "ff03", "ff04"}:
                continue

            try:
                await asyncio.wait_for(self.client.start_notify(characteristic.uuid, self._data_handler_cb), timeout=5.0)
                self._notify_shorts.add(short)
            except Exception:
                self.logger.debug("start_notify failed for %s", short, exc_info=True)

    async def _enable_notifications(self):
        writer = self._characteristics_by_short.get("ff03") or self._characteristics_by_short.get("ff02")
        if writer is None:
            writer = self._characteristics.get(str(self.ENABLE_UUID).lower())

        if writer is None:
            return

        self._query_writer_short = self._short_uuid(writer.uuid)

        payloads = [b"0100", b"\x01\x00"]
        for payload in payloads:
            try:
                await asyncio.wait_for(self.client.write_gatt_char(writer.uuid, payload), timeout=self.io_timeout)
                return
            except Exception:
                self.logger.debug("enable payload %r failed on %s", payload, self._query_writer_short, exc_info=True)

    async def _get_status_legacy(self, stop_event=None, probe=False, poll_reads_during_wait=False):
        status = await self._get_status_legacy_modbus(
            stop_event=stop_event,
            probe=probe,
            poll_reads_during_wait=poll_reads_during_wait,
        )
        if status is not None:
            return status

        if probe:
            return None

        raw_status = await self._get_status_legacy_single_frame(stop_event=stop_event)
        if raw_status is None:
            return None
        return self._parse_legacy_status(raw_status)

    async def _get_status_legacy_single_frame(self, stop_event=None):
        if self._future and not self._future.done():
            raise RuntimeError("A status request is already in progress")

        loop = asyncio.get_running_loop()
        self._loop = loop
        future = loop.create_future()
        self._future = future
        self._buffer.clear()

        stop_task = None
        try:
            wait_set = {future}
            if stop_event is not None:
                stop_task = asyncio.create_task(stop_event.wait())
                wait_set.add(stop_task)

            if self.debug_mppt:
                self.logger.debug("legacy single-frame TX start session=%s", self._session_id)
            await asyncio.wait_for(
                self.client.write_gatt_char(self.GET_STATUS_UUID, self.GET_STATUS_PAYLOAD),
                timeout=self.io_timeout,
            )
            if self.debug_mppt:
                self.logger.debug("legacy single-frame TX done waiting for response")

            done, _pending = await asyncio.wait(
                wait_set,
                timeout=self.request_timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if future in done:
                raw_status = future.result()
                if self.debug_mppt:
                    self.logger.debug("legacy single-frame RX len=%s", len(raw_status) if raw_status else None)
                return self._parse_legacy_status(raw_status)

            if stop_task is not None and stop_task in done:
                if not future.done():
                    future.cancel()
                raise asyncio.CancelledError()

            if not future.done():
                future.set_exception(TimeoutError("Timed out waiting for MPPT status"))
            raise TimeoutError("Timed out waiting for MPPT status")
        finally:
            if stop_task is not None:
                stop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stop_task
            if self._future is future:
                self._future = None
            if self._loop is loop:
                self._loop = None
            self._buffer.clear()

    async def _get_status_legacy_modbus(self, stop_event=None, probe=False, poll_reads_during_wait=False):
        if not probe:
            self._legacy_realtime_tick += 1

        used_writer = self._query_writer_short or "ff02"
        used_slave = 0xFE
        used_count = 0x2B
        timeout = 1.35 if probe else 1.80
        attempts = [
            (used_writer, used_slave, used_count, timeout),
            ("ff02", 0xFE, 0x2B, timeout),
            ("ff02", 0x01, 0x2B, timeout),
            ("ff03", 0x01, 0x2B, timeout),
            ("ff02", 0xFE, 0x29, timeout),
        ]

        seen = set()
        for writer_short, slave_id, register_count, timeout in attempts:
            key = (writer_short, slave_id, register_count)
            if key in seen:
                continue
            seen.add(key)
            if self.debug_mppt:
                self.logger.debug(
                    "legacy modbus attempt writer=%s sid=0x%02X count=0x%02X timeout=%.2f probe=%s",
                    writer_short,
                    slave_id,
                    register_count,
                    timeout,
                    probe,
                )

            frame = await self._query_modbus_block(
                start_address=0x3030,
                register_count=register_count,
                function_code=0x04,
                slave_ids=(slave_id,),
                timeout=timeout,
                stop_event=stop_event,
                forced_writer_short_uuid=writer_short,
                forced_modes=(False,),
                force_single_slave_id=True,
                poll_reads_during_wait=poll_reads_during_wait,
            )
            if frame is None:
                if self.debug_mppt:
                    self.logger.debug(
                        "legacy modbus miss writer=%s sid=0x%02X count=0x%02X",
                        writer_short,
                        slave_id,
                        register_count,
                    )
                continue

            if self.debug_mppt:
                self.logger.debug(
                    "legacy modbus hit writer=%s sid=0x%02X count=0x%02X frame_len=%s",
                    writer_short,
                    slave_id,
                    register_count,
                    len(frame),
                )
            status = self._decode_modbus_status(frame, start_address=0x3030, register_count=register_count)
            issues = self._status_plausibility_issues(status)
            if issues:
                self.logger.warning(
                    "ignoring implausible legacy realtime frame writer=%s sid=0x%02X count=0x%02X issues=%s",
                    writer_short,
                    slave_id,
                    register_count,
                    "; ".join(issues),
                )
                retry_frame = await self._query_modbus_block(
                    start_address=0x3030,
                    register_count=register_count,
                    function_code=0x04,
                    slave_ids=(slave_id,),
                    timeout=timeout,
                    stop_event=stop_event,
                    forced_writer_short_uuid=writer_short,
                    forced_modes=(False,),
                    force_single_slave_id=True,
                    poll_reads_during_wait=poll_reads_during_wait,
                )
                if retry_frame is None:
                    continue
                status = self._decode_modbus_status(retry_frame, start_address=0x3030, register_count=register_count)
                issues = self._status_plausibility_issues(status)
                if issues:
                    self.logger.warning(
                        "ignoring repeated implausible legacy realtime frame writer=%s sid=0x%02X count=0x%02X issues=%s",
                        writer_short,
                        slave_id,
                        register_count,
                        "; ".join(issues),
                    )
                    continue

            status["PekawayBLEMppt"]["protocol"]["mode"] = "legacy"
            status["PekawayBLEMppt"]["statusHints"].insert(0, "Legacy transport decoded via FC04 realtime block")

            if not probe and self._legacy_realtime_tick % 6 == 0:
                supplemental = await self._query_modbus_block(
                    start_address=0x30A0,
                    register_count=0x000C,
                    function_code=0x04,
                    slave_ids=(slave_id,),
                    timeout=0.50,
                    stop_event=stop_event,
                    forced_writer_short_uuid=writer_short,
                    forced_modes=(False,),
                    force_single_slave_id=True,
                    poll_reads_during_wait=poll_reads_during_wait,
                )
                if supplemental is not None:
                    status["PekawayBLEMppt"]["statusHints"].append("Supplemental 0x30A0 block observed")
                    status["PekawayBLEMppt"]["supplementalBatteryStats"] = self._decode_supplemental_block(supplemental)

            self._protocol_mode = "legacy"
            self._query_writer_short = writer_short
            self._protocol_hint = "legacy"
            return status

        return None

    async def _get_status_modern(self, stop_event=None, probe=False, poll_reads_during_wait=True):
        # The Blue app-style FC04 register block is the preferred realtime path.
        # Legacy devices may still end up here because they expose the same data
        # over the same register window.
        profiles = [
            (0xFE, 0x29),
            (0x01, 0x29),
            (0x01, 0x28),
            (0xFE, 0x28),
            (0xFE, 0x2B),
            (0x01, 0x2B),
        ]

        if probe:
            profiles = profiles[:3]

        for slave_id, register_count in profiles:
            if self.debug_mppt:
                self.logger.debug(
                    "modern modbus attempt sid=0x%02X count=0x%02X probe=%s",
                    slave_id,
                    register_count,
                    probe,
                )
            frame = await self._query_modbus_block(
                start_address=0x3030,
                register_count=register_count,
                function_code=0x04,
                slave_ids=(slave_id,),
                timeout=0.8 if probe else 1.5,
                stop_event=stop_event,
                poll_reads_during_wait=poll_reads_during_wait,
            )
            if frame is None:
                if self.debug_mppt:
                    self.logger.debug(
                        "modern modbus miss sid=0x%02X count=0x%02X",
                        slave_id,
                        register_count,
                    )
                continue

            if self.debug_mppt:
                self.logger.debug(
                    "modern modbus hit sid=0x%02X count=0x%02X frame_len=%s",
                    slave_id,
                    register_count,
                    len(frame),
                )
            status = self._decode_modbus_status(frame, start_address=0x3030, register_count=register_count)
            issues = self._status_plausibility_issues(status)
            if issues:
                self.logger.warning(
                    "ignoring implausible modern realtime frame sid=0x%02X count=0x%02X issues=%s",
                    slave_id,
                    register_count,
                    "; ".join(issues),
                )
                retry_frame = await self._query_modbus_block(
                    start_address=0x3030,
                    register_count=register_count,
                    function_code=0x04,
                    slave_ids=(slave_id,),
                    timeout=0.8 if probe else 1.5,
                    stop_event=stop_event,
                    poll_reads_during_wait=poll_reads_during_wait,
                )
                if retry_frame is None:
                    continue
                status = self._decode_modbus_status(retry_frame, start_address=0x3030, register_count=register_count)
                issues = self._status_plausibility_issues(status)
                if issues:
                    self.logger.warning(
                        "ignoring repeated implausible modern realtime frame sid=0x%02X count=0x%02X issues=%s",
                        slave_id,
                        register_count,
                        "; ".join(issues),
                    )
                    continue

            if probe:
                self._protocol_mode = "modern"
                return status

            supplemental = await self._query_modbus_block(
                start_address=0x30A0,
                register_count=0x000C,
                function_code=0x04,
                slave_ids=(slave_id,),
                timeout=1.0,
                stop_event=stop_event,
                poll_reads_during_wait=poll_reads_during_wait,
            )
            if supplemental is not None:
                status["PekawayBLEMppt"]["statusHints"].append("Supplemental 0x30A0 block observed")
                status["PekawayBLEMppt"]["supplementalBatteryStats"] = self._decode_supplemental_block(supplemental)

            self._protocol_mode = "modern"
            return status

        return None

    async def _query_history_snapshot(self, stop_event=None, running_days=None):
        # The app reads 60-day history from 0x3061 and total history from 0x309C.
        legacy_mode = self._protocol_mode == "legacy" or self._protocol_hint == "legacy"
        slave_ids = (0x01, 0xFE) if legacy_mode else (0xFE, 0x01)
        series_frame = await self._query_modbus_block(
            start_address=0x3061,
            register_count=60,
            function_code=0x04,
            slave_ids=slave_ids,
            timeout=1.6,
            stop_event=stop_event,
        )

        total_frame = await self._query_modbus_block(
            start_address=0x309C,
            register_count=1,
            function_code=0x04,
            slave_ids=slave_ids,
            timeout=1.2,
            stop_event=stop_event,
        )

        history = {
            "chargeLast60Kwh": [],
            "consumptionLast60Kwh": [],
            "charge1dKwh": None,
            "charge2dKwh": None,
            "charge3dKwh": None,
            "charge4dKwh": None,
            "charge60dKwh": None,
            "consumption1dKwh": None,
            "consumption2dKwh": None,
            "consumption3dKwh": None,
            "consumption4dKwh": None,
            "consumption60dKwh": None,
            "source": "modbus",
        }

        if series_frame is not None:
            words = self._extract_words_from_frame(series_frame)
            charge_series = [round(word / 100.0, 2) for word in words[:60]]
            charge_series = self._sanitize_history_kwh_series(charge_series)
            if running_days is not None:
                try:
                    active_days = max(0, min(int(running_days), len(charge_series)))
                except (TypeError, ValueError):
                    active_days = len(charge_series)
                for idx in range(active_days, len(charge_series)):
                    charge_series[idx] = 0.0
            history["chargeLast60Kwh"] = charge_series
            if charge_series:
                history["charge1dKwh"] = charge_series[0]
                if len(charge_series) > 1:
                    history["charge2dKwh"] = charge_series[1]
                if len(charge_series) > 2:
                    history["charge3dKwh"] = charge_series[2]
                if len(charge_series) > 3:
                    history["charge4dKwh"] = charge_series[3]
                history["charge60dKwh"] = charge_series[-1]

        if total_frame is not None:
            words = self._extract_words_from_frame(total_frame)
            if words:
                history["charge60dKwh"] = round(words[0] / 100.0, 2)

        return history

    async def _query_modbus_block(
        self,
        start_address,
        register_count,
        function_code=0x04,
        slave_ids=(0xFE, 0x01),
        timeout=1.2,
        stop_event=None,
        forced_writer_short_uuid=None,
        forced_modes=None,
        force_single_slave_id=False,
        poll_reads_during_wait=True,
    ):
        if not self.is_connected:
            raise ConnectionError("MPPT is not connected")

        writers = self._writer_candidates()
        if forced_writer_short_uuid is not None:
            forced = self._characteristics_by_short.get(forced_writer_short_uuid)
            writers = [forced] if forced is not None else []
        if not writers:
            return None

        expected_byte_count = register_count * 2
        stop_task = None
        if stop_event is not None:
            stop_task = asyncio.create_task(stop_event.wait())

        try:
            for writer in writers:
                writer_short = self._short_uuid(writer.uuid)
                modes = list(forced_modes) if forced_modes is not None else self._writer_modes(writer)
                for without_response in modes:
                    active_slave_ids = (slave_ids[:1] if force_single_slave_id else slave_ids)
                    for slave_id in active_slave_ids:
                        if self.debug_mppt:
                            self.logger.debug(
                                "modbus TX start writer=%s sid=0x%02X fc=0x%02X addr=0x%04X count=0x%02X noResp=%s pollReads=%s timeout=%.2f",
                                writer_short,
                                slave_id,
                                function_code,
                                start_address,
                                register_count,
                                without_response,
                                poll_reads_during_wait,
                                timeout,
                            )
                        self._modbus_capture = bytearray()
                        query = self._build_modbus_read_frame(
                            slave_id=slave_id,
                            function_code=function_code,
                            start_address=start_address,
                            register_count=register_count,
                        )
                        try:
                            await asyncio.wait_for(
                                self.client.write_gatt_char(
                                    writer.uuid,
                                    query,
                                    response=not without_response,
                                ),
                                timeout=self.io_timeout,
                            )
                        except Exception:
                            continue

                        end = monotonic() + timeout
                        while monotonic() < end:
                            if stop_task is not None and stop_task.done():
                                raise asyncio.CancelledError()

                            if poll_reads_during_wait:
                                await self._read_mppt_characteristics_once()
                            else:
                                await asyncio.sleep(0.08)
                            frame = self._extract_read_response_frame_from_stream(
                                self._modbus_capture,
                                function_code=function_code,
                                expected_byte_count=expected_byte_count,
                            )
                            if frame is None:
                                frame = self._extract_read_response_frame(
                                    self._frames.values(),
                                    function_code=function_code,
                                    expected_byte_count=expected_byte_count,
                                )
                            if frame is not None:
                                self._query_writer_short = writer_short
                                if self.debug_mppt:
                                    self.logger.debug(
                                        "modbus RX hit writer=%s sid=0x%02X fc=0x%02X addr=0x%04X count=0x%02X frame_len=%s",
                                        writer_short,
                                        slave_id,
                                        function_code,
                                        start_address,
                                        register_count,
                                        len(frame),
                                    )
                                return frame
                            await asyncio.sleep(0.08)
                        if self.debug_mppt:
                            self.logger.debug(
                                "modbus TX timeout writer=%s sid=0x%02X fc=0x%02X addr=0x%04X count=0x%02X noResp=%s",
                                writer_short,
                                slave_id,
                                function_code,
                                start_address,
                                register_count,
                                without_response,
                            )
                        self._modbus_capture = None
            return None
        finally:
            self._modbus_capture = None
            if stop_task is not None:
                stop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stop_task

    async def _read_mppt_characteristics_once(self):
        for short in ("ff01", "ff02", "ff03", "ff04"):
            characteristic = self._characteristics_by_short.get(short)
            if characteristic is None:
                continue
            if not self._char_has_property(characteristic, "read"):
                continue
            try:
                data = await asyncio.wait_for(self.client.read_gatt_char(characteristic.uuid), timeout=self.io_timeout)
            except Exception:
                continue
            if data:
                self._record_frame(short, data)

    def _data_handler_cb(self, characteristic, value):
        short = self._short_uuid(characteristic.uuid)
        self._record_frame(short, value)
        if self._modbus_capture is not None:
            self._modbus_capture.extend(value)

        if short == "ff01":
            self._buffer.extend(value)
            future = self._future
            if future and not future.done() and len(self._buffer) >= self.notification_min_length:
                future.set_result(bytes(self._buffer))
                self._buffer.clear()

    def _resolve_disconnect(self, future, exc):
        if future and not future.done():
            future.set_exception(exc)

    def _on_disconnected(self, _client, session_id=None):
        if session_id is not None and session_id != self._session_id:
            self.logger.info("ignoring late disconnect callback session=%s current=%s", session_id, self._session_id)
            return

        if self._disconnecting:
            return

        self.logger.warning("BLE device disconnected unexpectedly")
        future = self._future
        if future and not future.done():
            exc = ConnectionError("BLE device disconnected")
            loop = self._loop
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._resolve_disconnect, future, exc)
            else:
                self._resolve_disconnect(future, exc)

    def _record_frame(self, short, data):
        frame = bytes(data)
        self._frames[short] = frame
        if self._looks_like_modbus_read_response(frame):
            self._frames["modbus_read_last"] = frame
        if short == "ff03":
            self._frames["ff03"] = frame
        if short == "ff04":
            self._frames["ff04"] = frame

    def _decode_legacy_status(self, status):
        result = self._base_status_block(protocol="legacy", status_hints=["Legacy single-frame status response"])
        result["PekawayBLEMppt"]["soc"] = self._u8(status, 46)
        result["PekawayBLEMppt"]["pv"]["V"] = self._u16(status, 63) / 100
        result["PekawayBLEMppt"]["pv"]["A"] = self._s16(status, 65) / 100
        result["PekawayBLEMppt"]["pv"]["W"] = self._u16(status, 67) / 100
        result["PekawayBLEMppt"]["pv"]["total"] = self._u16(status, 73) / 100
        result["PekawayBLEMppt"]["batt"]["V"] = self._u16(status, 47) / 100
        result["PekawayBLEMppt"]["batt"]["A"] = self._s16(status, 49) / 100
        result["PekawayBLEMppt"]["batt"]["temp"] = self._u16(status, 17) / 100
        result["PekawayBLEMppt"]["load"]["V"] = self._u16(status, 55) / 100
        result["PekawayBLEMppt"]["load"]["A"] = self._s16(status, 57) / 100
        result["PekawayBLEMppt"]["load"]["W"] = self._u16(status, 59) / 100
        result["PekawayBLEMppt"]["load"]["total"] = self._u16(status, 79) / 100
        return result

    def _decode_modbus_status(self, frame, start_address, register_count):
        words = self._extract_words_from_frame(frame)
        register_map = {start_address + idx: word for idx, word in enumerate(words)}

        def reg(address):
            return register_map.get(address)

        result = self._base_status_block(
            protocol="modbus",
            status_hints=[
                f"Decoded realtime Modbus block (0x{start_address:04X}..0x{start_address + register_count - 1:04X}, FC04)",
            ],
        )

        result["PekawayBLEMppt"]["slaveId"] = reg(0x3030)
        result["PekawayBLEMppt"]["runningDays"] = reg(0x3031)
        result["PekawayBLEMppt"]["controllerStatusWord"] = reg(0x3032)
        result["PekawayBLEMppt"]["batteryStatusWord"] = reg(0x3033)
        result["PekawayBLEMppt"]["chargeStatusWord"] = reg(0x3034)
        result["PekawayBLEMppt"]["dischargeStatusWord"] = reg(0x3035)
        result["PekawayBLEMppt"]["batterySocPct"] = reg(0x3045)
        result["PekawayBLEMppt"]["batteryVoltageV"] = self._scaled(reg(0x3046), 100)
        result["PekawayBLEMppt"]["batteryCurrentA"] = self._scaled_signed16(reg(0x3047), 100)
        result["PekawayBLEMppt"]["batteryPowerW"] = self._scaled32(reg(0x3048), reg(0x3049), 100)
        result["PekawayBLEMppt"]["loadVoltageV"] = self._scaled(reg(0x304A), 100)
        result["PekawayBLEMppt"]["loadCurrentA"] = self._scaled(reg(0x304B), 100)
        result["PekawayBLEMppt"]["loadPowerW"] = self._scaled32(reg(0x304C), reg(0x304D), 100)
        result["PekawayBLEMppt"]["pvVoltageV"] = self._scaled(reg(0x304E), 100)
        result["PekawayBLEMppt"]["pvCurrentA"] = self._scaled(reg(0x304F), 100)
        result["PekawayBLEMppt"]["pvPowerW"] = self._scaled32(reg(0x3050), reg(0x3051), 100)
        result["PekawayBLEMppt"]["pvEnergyTodayKwh"] = self._scaled(reg(0x3052), 100)
        result["PekawayBLEMppt"]["pvEnergyTotalKwh"] = self._scaled32(reg(0x3053), reg(0x3054), 100)
        result["PekawayBLEMppt"]["loadEnergyTodayKwh"] = self._scaled(reg(0x3055), 100)
        result["PekawayBLEMppt"]["loadEnergyTotalKwh"] = self._scaled32(reg(0x3056), reg(0x3057), 100)
        result["PekawayBLEMppt"]["lightMinutesToday"] = reg(0x3058)
        result["PekawayBLEMppt"]["environmentTempC"] = self._scaled_signed16(reg(0x3036), 100)
        result["PekawayBLEMppt"]["controllerTempC"] = self._scaled_signed16(reg(0x3037), 100)

        battery_status = reg(0x3033)
        if battery_status is not None:
            temp_bits = (battery_status >> 4) & 0x0F
            volt_bits = battery_status & 0x0F
            if temp_bits == 0x01:
                result["PekawayBLEMppt"]["activeWarnings"].append("Battery high-temperature protection")
            if volt_bits == 0x01:
                result["PekawayBLEMppt"]["activeWarnings"].append("Battery over-voltage protection")
            if volt_bits == 0x02:
                result["PekawayBLEMppt"]["activeWarnings"].append("Battery voltage low")
            if volt_bits == 0x03:
                result["PekawayBLEMppt"]["activeWarnings"].append("Battery low-voltage protection")

        charge_status = reg(0x3034)
        if charge_status is not None:
            result["PekawayBLEMppt"]["dayNight"] = "Night" if ((charge_status >> 5) & 0x01) == 1 else "Day"
            charge_status_bits = (charge_status >> 2) & 0x03
            result["PekawayBLEMppt"]["chargeStage"] = {
                1: "Float",
                2: "Boost",
                3: "Equal",
            }.get(charge_status_bits, "Idle")
            if ((charge_status >> 4) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Charge over-temperature")
            result["PekawayBLEMppt"]["chargeFault"] = ((charge_status >> 1) & 0x01) == 1
            result["PekawayBLEMppt"]["chargeActive"] = (charge_status & 0x01) == 1

        discharge_status = reg(0x3035)
        if discharge_status is not None:
            output_level = (discharge_status >> 12) & 0x03
            if output_level == 0x03:
                result["PekawayBLEMppt"]["activeWarnings"].append("Load output overload")
            if ((discharge_status >> 11) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Load short circuit")
            if ((discharge_status >> 4) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Discharge hardware protection")
            if ((discharge_status >> 3) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Open-circuit protection")
            if ((discharge_status >> 2) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Discharge over-temperature")
            if ((discharge_status >> 1) & 0x01) == 1:
                result["PekawayBLEMppt"]["activeWarnings"].append("Discharge fault")
            result["PekawayBLEMppt"]["discharging"] = (discharge_status & 0x01) == 1

        self._inject_protocol_frames(result)
        self._inject_controller_temp_fallback(result)
        return result

    def _inject_protocol_frames(self, result):
        ff03 = self._frames.get("ff03")
        ff04 = self._frames.get("ff04")
        if ff03 is not None and len(ff03) >= 2:
            result["PekawayBLEMppt"]["ff03WordBe"] = self._u16_bytes(ff03, 0, big_endian=True)
            result["PekawayBLEMppt"]["ff03WordLe"] = self._u16_bytes(ff03, 0, big_endian=False)
        if ff04 is not None and len(ff04) >= 1:
            result["PekawayBLEMppt"]["ff04Byte"] = ff04[0]

        hints = result["PekawayBLEMppt"]["statusHints"]
        if ff03 is not None:
            hints.append(f"FF03 observed: {self._hex(ff03)}")
        if ff04 is not None:
            hints.append(f"FF04 observed: {self._hex(ff04)}")
        if ff03 is None and ff04 is None:
            hints.append("No FF03/FF04 protocol frames observed yet")

    def _inject_controller_temp_fallback(self, result):
        batt = result["PekawayBLEMppt"]["batt"]
        if batt.get("temp") is None:
            controller_temp = result["PekawayBLEMppt"].get("controllerTempC")
            environment_temp = result["PekawayBLEMppt"].get("environmentTempC")
            batt["temp"] = controller_temp if controller_temp is not None else environment_temp

    def _base_status_block(self, protocol, status_hints):
        return {
            "PekawayBLEMppt": {
                "soc": None,
                "pv": {
                    "V": None,
                    "A": None,
                    "W": None,
                    "total": None,
                },
                "batt": {
                    "V": None,
                    "A": None,
                    "temp": None,
                },
                "load": {
                    "V": None,
                    "A": None,
                    "W": None,
                    "total": None,
                },
                "protocol": {
                    "mode": protocol,
                    "writer": self._query_writer_short,
                },
                "statusHints": list(status_hints),
                "activeWarnings": [],
                "chargeFault": None,
                "chargeActive": None,
                "discharging": None,
                "dayNight": None,
                "chargeStage": None,
                "batteryPowerW": None,
                "loadPowerW": None,
                "pvEnergyTodayKwh": None,
                "pvEnergyTotalKwh": None,
                "loadEnergyTodayKwh": None,
                "loadEnergyTotalKwh": None,
                "batteryVoltageHighTodayV": None,
                "batteryVoltageLowTodayV": None,
                "batteryVoltageHigh1dAgoV": None,
                "batteryVoltageHigh2dAgoV": None,
                "batteryLowVoltageProtectionTimes": None,
                "batteryFullyChargedTimes": None,
                "environmentTempC": None,
                "controllerTempC": None,
                "slaveId": None,
                "runningDays": None,
                "controllerStatusWord": None,
                "batteryStatusWord": None,
                "chargeStatusWord": None,
                "dischargeStatusWord": None,
                "ff03WordBe": None,
                "ff03WordLe": None,
                "ff04Byte": None,
                "history": None,
            }
        }

    def _decode_supplemental_block(self, frame):
        words = self._extract_words_from_frame(frame)
        if len(words) < 12:
            return {"rawWords": words}

        return {
            "batteryLowVoltageProtectionTimes": words[6],
            "batteryFullyChargedTimes": words[7],
            "batteryVoltageHighTodayV": self._scaled(words[8], 100),
            "batteryVoltageLowTodayV": self._scaled(words[9], 100),
            "batteryVoltageHigh1dAgoV": self._scaled(words[10], 100),
            "batteryVoltageHigh2dAgoV": self._scaled(words[11], 100),
        }

    # Reject frames that decode cleanly but clearly violate physical constraints.
    def _status_plausibility_issues(self, status):
        root = (status or {}).get("PekawayBLEMppt", {})
        pv = root.get("pv", {})
        batt = root.get("batt", {})
        load = root.get("load", {})
        issues = []

        def first(*values):
            for value in values:
                if value is not None:
                    return value
            return None

        def add_range_issue(name, value, low, high):
            if value is None:
                return
            if value < low or value > high:
                issues.append(f"{name}={value} outside {low}..{high}")

        def add_power_issue(label, voltage, current, power):
            if voltage is None or current is None or power is None:
                return

            measured = abs(power)
            if measured > 100000.0:
                issues.append(f"{label} power={power}W is implausibly large")
                return

            expected = abs(voltage * current)
            if expected < 5.0 or measured < 5.0:
                return

            if voltage < 1.0 and abs(current) > 5.0:
                issues.append(f"{label} voltage/current combo looks invalid: {voltage}V, {current}A")
                return

            ratio = measured / expected if expected else float("inf")
            if ratio < 0.2 or ratio > 20.0:
                issues.append(
                    f"{label} power mismatch: {power}W vs {voltage}V * {current}A"
                )

        battery_voltage = first(root.get("batteryVoltageV"), batt.get("V"))
        battery_current = first(root.get("batteryCurrentA"), batt.get("A"))
        battery_power = first(root.get("batteryPowerW"), batt.get("W"))
        load_voltage = first(root.get("loadVoltageV"), load.get("V"))
        load_current = first(root.get("loadCurrentA"), load.get("A"))
        load_power = first(root.get("loadPowerW"), load.get("W"))
        pv_voltage = first(root.get("pvVoltageV"), pv.get("V"))
        pv_current = first(root.get("pvCurrentA"), pv.get("A"))
        pv_power = first(root.get("pvPowerW"), pv.get("W"))
        temp_c = first(root.get("controllerTempC"), batt.get("temp"))
        environment_temp_c = root.get("environmentTempC")

        add_range_issue("batteryVoltageV", battery_voltage, 0.0, 120.0)
        add_range_issue("loadVoltageV", load_voltage, 0.0, 120.0)
        add_range_issue("pvVoltageV", pv_voltage, 0.0, 500.0)
        add_range_issue("environmentTempC", environment_temp_c, -40.0, 125.0)
        add_range_issue("controllerTempC", temp_c, -40.0, 125.0)

        add_power_issue("pv", pv_voltage, pv_current, pv_power)
        add_power_issue("battery", battery_voltage, battery_current, battery_power)
        add_power_issue("load", load_voltage, load_current, load_power)

        return issues

    def _parse_legacy_status(self, status):
        result = self._base_status_block(protocol="legacy", status_hints=["Legacy single-frame status response"])
        result["PekawayBLEMppt"]["soc"] = self._u8(status, 46)
        result["PekawayBLEMppt"]["pv"]["V"] = self._u16(status, 63) / 100
        result["PekawayBLEMppt"]["pv"]["A"] = self._s16(status, 65) / 100
        result["PekawayBLEMppt"]["pv"]["W"] = self._u16(status, 67) / 100
        result["PekawayBLEMppt"]["pv"]["total"] = self._u16(status, 73) / 100
        result["PekawayBLEMppt"]["batt"]["V"] = self._u16(status, 47) / 100
        result["PekawayBLEMppt"]["batt"]["A"] = self._s16(status, 49) / 100
        result["PekawayBLEMppt"]["batt"]["temp"] = self._u16(status, 17) / 100
        result["PekawayBLEMppt"]["load"]["V"] = self._u16(status, 55) / 100
        result["PekawayBLEMppt"]["load"]["A"] = self._s16(status, 57) / 100
        result["PekawayBLEMppt"]["load"]["W"] = self._u16(status, 59) / 100
        result["PekawayBLEMppt"]["load"]["total"] = self._u16(status, 79) / 100
        result["PekawayBLEMppt"]["protocol"]["mode"] = "legacy"
        result["PekawayBLEMppt"]["protocol"]["writer"] = "ff02"
        self._inject_protocol_frames(result)
        return result

    def _build_modbus_read_frame(self, slave_id, function_code, start_address, register_count):
        pdu = [
            slave_id & 0xFF,
            function_code & 0xFF,
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (register_count >> 8) & 0xFF,
            register_count & 0xFF,
        ]
        crc = self._crc16_modbus(pdu)
        return bytes([*pdu, crc & 0xFF, (crc >> 8) & 0xFF])

    def _extract_read_response_frame(self, frames, function_code, expected_byte_count):
        for frame in frames:
            if len(frame) >= 3 and frame[1] == function_code and frame[2] == expected_byte_count:
                payload_end = 3 + expected_byte_count
                if len(frame) == payload_end:
                    return bytes(frame[:payload_end])
                if len(frame) >= payload_end + 2:
                    crc = (frame[payload_end + 1] << 8) | frame[payload_end]
                    if self._crc16_modbus(frame[:payload_end]) == crc:
                        return bytes(frame[:payload_end])
            if len(frame) >= 2 and frame[0] == function_code and frame[1] == expected_byte_count:
                payload_end = 2 + expected_byte_count
                if len(frame) == payload_end:
                    return bytes([0x01, *frame[:payload_end]])
        return None

    def _extract_read_response_frame_from_stream(self, stream, function_code, expected_byte_count):
        if not stream:
            return None

        data = bytes(stream)
        if len(data) < 3:
            return None

        for idx in range(0, len(data) - 2):
            if data[idx + 1] == function_code and data[idx + 2] == expected_byte_count:
                end = idx + 3 + expected_byte_count
                if len(data) == end:
                    return data[idx:end]
                if len(data) >= end + 2:
                    crc = (data[end + 1] << 8) | data[end]
                    if self._crc16_modbus(data[idx:end]) == crc:
                        return data[idx:end]
            if data[idx] == function_code and data[idx + 1] == expected_byte_count:
                end = idx + 2 + expected_byte_count
                if len(data) >= end:
                    if len(data) == end:
                        return bytes([0x01, *data[idx:end]])
        return None

    def _extract_words_from_frame(self, frame):
        if frame is None or len(frame) < 3:
            return []
        byte_count = frame[2]
        out = []
        for i in range(0, byte_count, 2):
            if 3 + i + 1 >= len(frame):
                break
            out.append(((frame[3 + i] << 8) | frame[3 + i + 1]) & 0xFFFF)
        return out

    def _looks_like_modbus_read_response(self, frame):
        if len(frame) >= 3 and frame[0] == 0x01 and frame[1] in (0x03, 0x04):
            byte_count = frame[2]
            return byte_count > 0 and len(frame) >= 3 + byte_count
        if len(frame) >= 2 and frame[0] in (0x03, 0x04):
            byte_count = frame[1]
            return byte_count > 0 and len(frame) >= 2 + byte_count
        return False

    def _writer_candidates(self):
        writers = []
        for short in ("ff02", "ff03", "ff01", "ff04"):
            characteristic = self._characteristics_by_short.get(short)
            if characteristic is None:
                continue
            if self._char_has_property(characteristic, "write") or self._char_has_property(
                characteristic, "writewithoutresponse"
            ):
                writers.append(characteristic)
        if writers:
            return writers
        for characteristic in self._characteristics.values():
            if self._char_has_property(characteristic, "write") or self._char_has_property(
                characteristic, "writewithoutresponse"
            ):
                writers.append(characteristic)
        return writers

    def _writer_modes(self, characteristic):
        props = self._properties(characteristic)
        modes = []
        if "writewithoutresponse" in props:
            modes.append(True)
        if "write" in props:
            modes.append(False)
        if not modes:
            modes = [False, True]
        return modes

    def _char_has_property(self, characteristic, prop):
        return self._normalize_token(prop) in self._properties(characteristic)

    def _properties(self, characteristic):
        props = getattr(characteristic, "properties", [])
        return {self._normalize_token(prop) for prop in props}

    def _normalize_token(self, value):
        return str(value).lower().replace("-", "").replace("_", "").replace(" ", "")

    def _short_uuid(self, value):
        text = str(value).lower()
        if text.startswith("0000") and text.endswith("-0000-1000-8000-00805f9b34fb"):
            return text[4:8]
        if len(text) == 4:
            return text
        if "ff01" in text:
            return "ff01"
        if "ff02" in text:
            return "ff02"
        if "ff03" in text:
            return "ff03"
        if "ff04" in text:
            return "ff04"
        return text

    def _u8(self, data, offset):
        if offset >= len(data):
            return None
        return data[offset]

    def _u16(self, data, offset):
        if offset + 1 >= len(data):
            return None
        return (data[offset] << 8) | data[offset + 1]

    def _s16(self, data, offset):
        value = self._u16(data, offset)
        if value is None:
            return None
        return value if value < 0x8000 else value - 0x10000

    def _u16_bytes(self, data, offset, big_endian=True):
        if offset + 1 >= len(data):
            return None
        if big_endian:
            return (data[offset] << 8) | data[offset + 1]
        return (data[offset + 1] << 8) | data[offset]

    def _scaled(self, raw, factor):
        if raw is None or factor == 0:
            return None
        return raw / factor

    def _scaled_signed16(self, raw, factor):
        if raw is None or factor == 0:
            return None
        if raw >= 0x8000:
            raw -= 0x10000
        return raw / factor

    def _scaled32(self, low_word, high_word, factor):
        if low_word is None or high_word is None or factor == 0:
            return None
        combined = ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)
        return combined / factor

    def _crc16_modbus(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF

    def _hex(self, data):
        if not data:
            return "(empty)"
        return " ".join(f"{b:02X}" for b in data)


def _install_stop_handlers(stop_event):
    loop = asyncio.get_running_loop()

    def request_stop():
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, request_stop)
        loop.add_signal_handler(signal.SIGTERM, request_stop)
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda *_: stop_event.set())
        signal.signal(signal.SIGTERM, lambda *_: stop_event.set())


async def main(mac_address, include_history=True, debug_mppt=False):
    logging.basicConfig(
        level=logging.DEBUG if debug_mppt else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    stop_event = asyncio.Event()
    mppt = PekawayBleMppt(logger=logger, debug_mppt=debug_mppt)

    _install_stop_handlers(stop_event)

    reconnect_delay = 5.0
    disconnect_streak = 0

    try:
        logger.info("running initial bluetoothctl disconnect before first ble connect mac=%s", mac_address)
        await mppt.hard_reset_bluetooth(mac_address)

        while not stop_event.is_set():
            try:
                if not mppt.is_connected:
                    await mppt.connect(mac_address)

                status = await mppt.get_status(stop_event=stop_event, include_history=include_history)
                if status is None:
                    raise TimeoutError("MPPT status unavailable")
                print(json.dumps(status, indent=2, sort_keys=True, ensure_ascii=False), flush=True)

                reconnect_delay = 5.0
                disconnect_streak = 0
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=MPPT_STATUS_POLL_INTERVAL)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("MPPT poll cycle failed")
                await mppt.disconnect()
                disconnect_streak += 1

                if disconnect_streak >= BLE_HARD_RESET_THRESHOLD:
                    await mppt.hard_reset_bluetooth(mac_address)
                    disconnect_streak = 0

                if stop_event.is_set():
                    break

                logger.info("Retrying BLE connection in %.1f seconds", reconnect_delay)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=reconnect_delay)
                except asyncio.TimeoutError:
                    reconnect_delay = min(reconnect_delay * 2, 30.0)
    finally:
        await mppt.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pekaway MPPT BLE poller")
    parser.add_argument("mac_address", help="BLE MAC address of the MPPT")
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="disable MPPT history snapshot in the printed JSON object",
    )
    parser.add_argument(
        "--debug-mppt",
        action="store_true",
        help="enable verbose MPPT protocol diagnostics",
    )
    args = parser.parse_args()

    asyncio.run(main(args.mac_address, include_history=not args.no_history, debug_mppt=args.debug_mppt))
