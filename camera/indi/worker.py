#!/usr/bin/env python3
"""RabbitMQ worker that captures a single INDI CCD exposure per task.

The important diagnostic is the CCD_EXPOSURE state log. A single task sends
exactly one sendNewNumber() command; if the INDI driver reports BUSY -> OK ->
BUSY again, or the remaining-time value jumps upward while BUSY, that points to
a restart in the driver/camera or another INDI client rather than this worker
issuing a second exposure command.
"""

import io
import json
import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pika
import PyIndi
from astropy.io import fits


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INDI_HOST = os.getenv("INDI_HOST", "indi")
INDI_PORT = int(os.getenv("INDI_PORT", "7624"))
INDI_CAMERA_NAME = os.getenv("INDI_CAMERA_NAME", "").strip()
INDI_BLOB_PROPERTY = os.getenv("INDI_BLOB_PROPERTY", "CCD1")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE_CAMERA", "camera")

FITS_PATH = Path(os.getenv("FITS_PATH", "/fits/current.fit"))
TELESCOPE_NAME = os.getenv("TELESCOPE_NAME", "AllSky")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Avoid sending a new exposure request if INDI says that an exposure is active.
CAMERA_IDLE_TIMEOUT = float(os.getenv("CAMERA_IDLE_TIMEOUT", "10"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s camera-worker2: %(message)s",
)
log = logging.getLogger("camera-worker2")


# ---------------------------------------------------------------------------
# INDI helpers
# ---------------------------------------------------------------------------

def _property_state(prop):
    """Return a readable INDI property state across pyindi-client versions."""
    candidates = [prop]
    try:
        if len(prop) > 0:
            candidates.append(prop[0])
    except Exception:
        pass

    state_names = {
        getattr(PyIndi, "IPS_IDLE", object()): "IDLE",
        getattr(PyIndi, "IPS_OK", object()): "OK",
        getattr(PyIndi, "IPS_BUSY", object()): "BUSY",
        getattr(PyIndi, "IPS_ALERT", object()): "ALERT",
    }
    for obj in candidates:
        method = getattr(obj, "getStateAsString", None)
        if callable(method):
            try:
                return str(method()).upper()
            except Exception:
                pass
        method = getattr(obj, "getState", None)
        if callable(method):
            try:
                state = method()
                return state_names.get(state, str(state).upper())
            except Exception:
                pass
    return None


def _number_value(prop):
    """Read CCD_EXPOSURE_VALUE (falling back to the first number element)."""
    try:
        for element in prop:
            if element.getName() == "CCD_EXPOSURE_VALUE":
                return float(element.getValue())
        if len(prop) > 0:
            return float(prop[0].getValue())
    except Exception:
        pass
    return None


def _set_number_value(prop, widget_name, value):
    """Set exactly one widget in a number vector; never loop over all widgets."""
    for element in prop:
        if element.getName() == widget_name:
            element.setValue(float(value))
            return
    if len(prop) == 1:
        prop[0].setValue(float(value))
        return
    raise RuntimeError(
        f"INDI number property has no widget {widget_name!r}; "
        f"available={[element.getName() for element in prop]}"
    )


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super().__init__()
        self.camera = None

        self._blob_lock = threading.Lock()
        self._blob_data = None
        self._blob_format = None
        self._accept_blob = False
        self._blobs_received = threading.Event()

        self._exposure_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._last_exposure_state = None
        self._last_exposure_value = None
        self._commanded_exposure = None
        self._exposure_command_time = None

    def newDevice(self, device):
        log.info("INDI device discovered: %s", device.getDeviceName())

    def removeDevice(self, device):
        log.warning("INDI device removed: %s", device.getDeviceName())

    def newProperty(self, prop):
        if prop.getName() in ("CCD_EXPOSURE", INDI_BLOB_PROPERTY):
            log.debug(
                "INDI property discovered: device=%s name=%s type=%s",
                prop.getDeviceName(), prop.getName(), prop.getTypeAsString(),
            )

    def removeProperty(self, prop):
        log.debug("INDI property removed: %s/%s", prop.getDeviceName(), prop.getName())

    def updateProperty(self, prop):
        try:
            if self.camera is None:
                return
            if prop.getDeviceName() != self.camera.getDeviceName():
                return

            # Instrument the exposure lifecycle. State changes are the key clue
            # for distinguishing a second exposure from slow readout/upload.
            if prop.getName() == "CCD_EXPOSURE" and prop.getType() == PyIndi.INDI_NUMBER:
                self._log_exposure_update(PyIndi.PropertyNumber(prop))
                return

            if prop.getName() != INDI_BLOB_PROPERTY or prop.getType() != PyIndi.INDI_BLOB:
                return

            blob_property = PyIndi.PropertyBlob(prop)
            if blob_property is None or blob_property.isEmpty():
                return

            blob = blob_property[0]
            if blob is None:
                return

            blob_len = int(blob.getBlobLen())
            if blob_len <= 0:
                return

            raw = blob.getblobdata()
            if raw is None:
                # Compatibility with pyindi-client versions exposing getBlob().
                raw = blob.getBlob()
            if raw is None:
                return

            self._store_blob(bytes(raw), blob.getFormat(), blob_property.getName(), "updateProperty")
        except Exception:
            log.exception("Error processing INDI property update")

    def _log_exposure_update(self, prop):
        state = _property_state(prop)
        value = _number_value(prop)
        now = time.monotonic()

        with self._state_lock:
            previous_state = self._last_exposure_state
            previous_value = self._last_exposure_value
            self._last_exposure_state = state
            self._last_exposure_value = value
            commanded = self._commanded_exposure
            command_time = self._exposure_command_time

        if state is not None and state != previous_state:
            elapsed = now - command_time if command_time is not None else None
            if elapsed is not None and commanded is not None:
                log.info(
                    "CCD_EXPOSURE state: %s -> %s, value=%s, %.3fs since command (requested=%.6fs)",
                    previous_state or "UNKNOWN", state,
                    f"{value:.6f}" if value is not None else "unknown",
                    elapsed, commanded,
                )
            else:
                log.info(
                    "CCD_EXPOSURE state: %s -> %s, value=%s",
                    previous_state or "UNKNOWN", state,
                    f"{value:.6f}" if value is not None else "unknown",
                )

        # CCD_EXPOSURE normally reports the remaining time while BUSY. If that
        # value increases materially without a new command, report a likely reset.
        if (
            state == "BUSY"
            and previous_state == "BUSY"
            and value is not None
            and previous_value is not None
            and value > previous_value + max(0.25, (commanded or 0.0) * 0.10)
        ):
            log.warning(
                "CCD_EXPOSURE remaining time increased while BUSY: %.3fs -> %.3fs; "
                "this worker sent only one command for the current task",
                previous_value, value,
            )
        elif LOG_LEVEL == "DEBUG" and state is not None:
            log.debug("CCD_EXPOSURE update: state=%s value=%s", state, value)

    def _store_blob(self, data, blob_format, blob_name, source):
        if not data:
            return

        with self._blob_lock:
            if not self._accept_blob:
                log.warning(
                    "Ignoring BLOB received outside an active capture: source=%s name=%s bytes=%d",
                    source, blob_name, len(data),
                )
                return
            if self._blob_data is not None:
                log.warning(
                    "Ignoring additional BLOB for the same task: source=%s name=%s bytes=%d",
                    source, blob_name, len(data),
                )
                return

            self._blob_data = data
            self._blob_format = blob_format
            self._accept_blob = False
            self._blobs_received.set()

        log.info(
            "BLOB received: source=%s name=%s bytes=%d format=%s",
            source, blob_name, len(data), blob_format,
        )

    # Older pyindi-client builds may use newBlob; newer ones commonly dispatch
    # through updateProperty. Keep these callbacks as compatibility fallbacks.
    def newBlob(self, bp):
        self._capture_legacy_blob(bp, "newBlob")

    def newBLOB(self, bp):
        try:
            for blob in bp:
                self._capture_legacy_blob(blob, "newBLOB")
        except TypeError:
            self._capture_legacy_blob(bp, "newBLOB")
        except Exception:
            log.exception("newBLOB callback failed")

    def _capture_legacy_blob(self, blob, source):
        try:
            blob_len = int(blob.getBlobLen())
            if blob_len <= 0:
                return
            data = blob.getBlob()
            if data is None:
                data = blob.getblobdata()
            if data is None:
                return
            self._store_blob(bytes(data), blob.getFormat(), blob.getName(), source)
        except Exception:
            log.exception("%s callback failed", source)

    def newBlobDone(self, bp, blob_file):
        log.debug("INDI BLOB transfer complete: %s", blob_file)

    def newMessage(self, device, message_id):
        try:
            message = device.messageQueue(message_id)
        except Exception:
            log.exception("Cannot read INDI message %s", message_id)
            message = "<message unavailable>"

        log.info(
            "INDI message from %s [id=%s]: %s",
            device.getDeviceName(),
            message_id,
            message,
        )

    def serverConnected(self):
        log.info("Connected to INDI server %s:%s", INDI_HOST, INDI_PORT)

    def serverDisconnected(self, code):
        log.warning("Disconnected from INDI server %s:%s code=%s", INDI_HOST, INDI_PORT, code)

    def prepare_for_blob(self):
        with self._blob_lock:
            self._blob_data = None
            self._blob_format = None
            self._accept_blob = True
        self._blobs_received.clear()

    def cancel_blob_wait(self):
        with self._blob_lock:
            self._accept_blob = False

    def wait_for_blob(self, timeout):
        if not self._blobs_received.wait(timeout):
            self.cancel_blob_wait()
            return None, None
        with self._blob_lock:
            return self._blob_data, self._blob_format

    def mark_exposure_command(self, exposure):
        with self._state_lock:
            self._commanded_exposure = float(exposure)
            self._exposure_command_time = time.monotonic()
            # Reset the value baseline so the first update isn't mistaken for a reset.
            self._last_exposure_value = None


# ---------------------------------------------------------------------------
# Camera setup and capture
# ---------------------------------------------------------------------------

def select_camera(indi, known_models=("QHY", "ZWO", "ASI", "Atik", "SBIG", "SX", "Simulator")):
    deadline = time.monotonic() + 10
    devices = []
    while time.monotonic() < deadline:
        devices = list(indi.getDevices())
        if devices:
            break
        time.sleep(0.1)

    if INDI_CAMERA_NAME:
        for device in devices:
            if device.getDeviceName() == INDI_CAMERA_NAME:
                return device
        raise RuntimeError(f"INDI_CAMERA_NAME={INDI_CAMERA_NAME!r} not found; devices="
                           f"{[d.getDeviceName() for d in devices]}")

    for model in known_models:
        for device in devices:
            if model.lower() in device.getDeviceName().lower():
                return device

    if devices:
        return devices[0]
    raise RuntimeError("No INDI devices found")


def connect_camera(indi, camera):
    name = camera.getDeviceName()
    indi.camera = camera  # Must be set before INDI callbacks can deliver a BLOB.

    log.info("Connecting camera: %s", name)
    conn_prop = camera.getProperty("CONNECTION")
    if conn_prop is None:
        raise RuntimeError(f"Camera {name!r} has no CONNECTION property")

    switches = conn_prop.getSwitch()
    for element in switches:
        element.setState(1 if element.getName() == "CONNECT" else 0)
    indi.sendNewSwitch(conn_prop)

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not camera.isConnected():
        time.sleep(0.1)
    if not camera.isConnected():
        raise RuntimeError(f"Camera {name!r} did not connect")
    log.info("Camera connected: %s", name)

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        exposure_prop = camera.getNumber("CCD_EXPOSURE")
        blob_prop = camera.getBLOB(INDI_BLOB_PROPERTY)
        if exposure_prop is not None and blob_prop is not None:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(
            f"Required properties not received: CCD_EXPOSURE and {INDI_BLOB_PROPERTY}"
        )

    indi.setBLOBMode(PyIndi.B_ALSO, name, INDI_BLOB_PROPERTY)
    log.info("BLOB mode enabled for %s/%s", name, INDI_BLOB_PROPERTY)
    time.sleep(1)


def _wait_until_camera_idle(camera, timeout=CAMERA_IDLE_TIMEOUT):
    """Do not accidentally submit a command while the prior capture is BUSY."""
    deadline = time.monotonic() + timeout
    last_state = None
    while time.monotonic() < deadline:
        prop = camera.getNumber("CCD_EXPOSURE")
        if prop is None:
            raise RuntimeError("CCD_EXPOSURE property disappeared")
        state = _property_state(prop)
        if state != last_state and state is not None:
            log.debug("Camera idle check: CCD_EXPOSURE state=%s", state)
            last_state = state
        if state != "BUSY":
            return
        time.sleep(0.1)
    raise TimeoutError(
        f"Camera remained BUSY for {timeout:.1f}s; refusing to send another exposure command"
    )


def set_binning(camera, indi, binning):
    prop = camera.getNumber("CCD_BINNING")
    if prop is None:
        log.warning("Task requested bin=%s but camera has no CCD_BINNING property; using bin=1", binning)
        return

    binning = int(binning)
    # Check what the camera actually supports
    hor = None
    ver = None
    for el in prop:
        if el.getName() == "HOR_BIN":
            hor = el
        elif el.getName() == "VER_BIN":
            ver = el
        else:
            if hor is None:
                hor = el
            elif ver is None:
                ver = el

    if hor is None:
        log.warning("Task requested bin=%s but camera has no HOR_BIN widget; using bin=1", binning)
        return

    supported_min = int(hor.getMin())
    supported_max = int(hor.getMax())
    supported_step = int(hor.getStep())
    if supported_max <= supported_min:
        log.warning("Camera CCD_BINNING not supported (min=%d max=%d); ignoring bin=%s", supported_min, supported_max, binning)
        return

    actual = binning
    if binning < supported_min:
        log.warning("Requested bin=%d < supported min=%d; using bin=%d", binning, supported_min, supported_min)
        actual = supported_min
    elif binning > supported_max:
        log.warning("Requested bin=%d > supported max=%d; using bin=%d", binning, supported_max, supported_max)
        actual = supported_max
    elif supported_step > 0 and (actual - supported_min) % supported_step != 0:
        actual = supported_min + round((actual - supported_min) / supported_step) * supported_step
        log.warning("Requested bin=%d not aligned to step=%d; using bin=%d", binning, supported_step, actual)

    log.info("Setting binning: requested=%d actual=%d (supported %d..%d step=%d)",
             binning, actual, supported_min, supported_max, supported_step)

    if hor:
        hor.setValue(float(actual))
    if ver:
        ver.setValue(float(actual))
    indi.sendNewNumber(prop)
    log.info("Binning command sent: HOR=%d VER=%d", actual, actual)


def set_gain(camera, indi, gain):
    prop = camera.getNumber("CCD_GAIN")
    if prop is None:
        log.warning("Task requested gain=%s but camera has no CCD_GAIN property", gain)
        return

    # CCD_GAIN usually has one widget. If the driver uses a different name,
    # setting its only widget is safe; avoid sending the same value repeatedly.
    if len(prop) == 1:
        element = prop[0]
    else:
        matching = [item for item in prop if item.getName() in ("GAIN", "CCD_GAIN_VALUE")]
        if len(matching) != 1:
            raise RuntimeError(
                f"Cannot identify gain widget; available={[item.getName() for item in prop]}"
            )
        element = matching[0]

    element.setValue(float(gain))
    indi.sendNewNumber(prop)
    log.info("Gain command sent: %s", gain)


def expose(camera, indi, exposure):
    exposure = float(exposure)
    if exposure <= 0:
        raise ValueError(f"Exposure must be > 0, got {exposure}")

    with indi._exposure_lock:
        _wait_until_camera_idle(camera)
        exposure_prop = camera.getNumber("CCD_EXPOSURE")
        if exposure_prop is None:
            raise RuntimeError("CCD_EXPOSURE property not available")

        # Prepare the receive side before sending the one and only trigger.
        indi.prepare_for_blob()
        _set_number_value(exposure_prop, "CCD_EXPOSURE_VALUE", exposure)
        indi.mark_exposure_command(exposure)

        # Intentionally exactly one sendNewNumber per RabbitMQ task.
        started = time.monotonic()
        log.info("Sending single CCD_EXPOSURE command: requested=%.6fs", exposure)
        indi.sendNewNumber(exposure_prop)
        log.info("CCD_EXPOSURE command sent; awaiting BLOB")

        # Some drivers require significant time for download/transfer after the
        # sensor exposure. Allow >2x requested time so diagnostics can complete.
        timeout = max(30.0, exposure * 3.0 + 10.0)
        data, blob_format = indi.wait_for_blob(timeout)
        elapsed = time.monotonic() - started
        log.info(
            "Capture wait finished: requested=%.6fs elapsed=%.3fs ratio=%.2f",
            exposure, elapsed, elapsed / exposure,
        )
        if data is None:
            raise TimeoutError(
                f"No BLOB received after {timeout:.1f}s for exposure={exposure}s"
            )
        return data, blob_format


def save_fits(data, exposure, gain, binning):
    FITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = FITS_PATH.with_name(FITS_PATH.name + ".tmp")

    with fits.open(io.BytesIO(data), mode="readonly") as source:
        output = fits.HDUList([hdu.copy() for hdu in source])
        try:
            output[0].header["TELESCOP"] = (TELESCOPE_NAME, "Telescope / camera system")
            output[0].header["DATE-OBS"] = (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "Observation timestamp",
            )
            output[0].header["EXPTIME"] = (float(exposure), "Requested exposure time (s)")
            output[0].header["GAIN"] = (float(gain) if gain else 0, "Camera gain")
            output[0].header["XBINNING"] = (int(binning) if binning else 1, "Horizontal binning")
            output[0].header["YBINNING"] = (int(binning) if binning else 1, "Vertical binning")
            output.writeto(tmp_path, overwrite=True)
        finally:
            output.close()

    os.replace(tmp_path, FITS_PATH)
    log.info("FITS saved to %s", FITS_PATH)


def is_fits(data):
    return data is not None and len(data) >= 9 and data[:9] == b"SIMPLE  ="


def parse_task(body):
    task = json.loads(body if isinstance(body, str) else body.decode("utf-8"))
    if not isinstance(task, dict) or "exposure" not in task:
        raise ValueError("Task must be a JSON object containing 'exposure'")
    return task


# ---------------------------------------------------------------------------
# RabbitMQ worker
# ---------------------------------------------------------------------------

class Worker:
    def __init__(self):
        self.indi = IndiClient()
        self.camera = None
        self.rabbit_connection = None
        self.rabbit_channel = None
        self.stopping = False

    def run(self):
        # The udev setup is intentionally run once, not both at import and here.
        udev_script = "/common/udev.py"
        if os.path.exists(udev_script):
            result = os.system(f"python3 {udev_script}")
            if result != 0:
                log.warning("udev setup exited with status=%s", result)

        log.info("Connecting to INDI server %s:%s", INDI_HOST, INDI_PORT)
        self.indi.setServer(INDI_HOST, INDI_PORT)
        if not self.indi.connectServer():
            raise RuntimeError("Cannot connect to INDI server")

        self.camera = select_camera(self.indi)
        log.info("Selected camera: %s", self.camera.getDeviceName())
        connect_camera(self.indi, self.camera)

        log.info("Connecting to RabbitMQ %s:%s", RABBITMQ_HOST, RABBITMQ_PORT)
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=0,  # The synchronous exposure callback can outlast heartbeat=60.
            blocked_connection_timeout=30,
        )
        self.rabbit_connection = pika.BlockingConnection(params)
        self.rabbit_channel = self.rabbit_connection.channel()
        self.rabbit_channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        self.rabbit_channel.basic_qos(prefetch_count=1)
        self.rabbit_channel.basic_consume(
            queue=RABBITMQ_QUEUE,
            on_message_callback=self.on_message,
            auto_ack=False,
        )

        log.info("Ready; queue=%s", RABBITMQ_QUEUE)
        try:
            while not self.stopping:
                self.rabbit_connection.process_data_events(time_limit=1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _reply(self, properties, body):
        if not properties.reply_to or not self.rabbit_channel or not self.rabbit_channel.is_open:
            return
        self.rabbit_channel.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=body,
        )

    def on_message(self, channel, method, properties, body):
        task_start = time.monotonic()
        exposure = None
        try:
            task = parse_task(body)
            exposure = float(task["exposure"])
            gain = task.get("gain")
            log.info("Task received: exposure=%.6fs gain=%s", exposure, gain)

            if gain is not None:
                set_gain(self.camera, self.indi, gain)

            binning = task.get("bin")
            if binning is not None:
                set_binning(self.camera, self.indi, binning)

            data, blob_format = expose(self.camera, self.indi, exposure)
            if not is_fits(data):
                prefix = data[:32] if data is not None else None
                raise RuntimeError(f"BLOB is not FITS data: {prefix!r}")

            actual_binning = 1
            try:
                bin_prop = self.camera.getNumber("CCD_BINNING")
                if bin_prop:
                    for el in bin_prop:
                        if el.getName() == "HOR_BIN":
                            actual_binning = int(round(el.getValue()))
                            break
            except Exception:
                log.warning("Cannot read CCD_BINNING from camera after capture")
            log.info("Actual binning used for this capture: %d (requested=%s)", actual_binning, binning)

            save_fits(data, exposure, gain, actual_binning)
            elapsed = time.monotonic() - task_start
            log.info(
                "Task complete: exposure=%.6fs format=%s total_elapsed=%.3fs",
                exposure, blob_format, elapsed,
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            try:
                self._reply(properties, b"Ok")
            except Exception:
                log.exception("Task succeeded, but the reply could not be published")

        except Exception as exc:
            log.exception("Task failed (exposure=%s): %s", exposure, exc)
            try:
                self.indi.cancel_blob_wait()
            except Exception:
                pass
            try:
                self._reply(properties, f"Error: {exc}".encode("utf-8", errors="replace"))
            except Exception:
                log.exception("Failed to publish task error reply")
            try:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception:
                log.exception("Failed to nack task")

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        log.info("Stopping worker")
        for connection in (self.rabbit_channel, self.rabbit_connection):
            if connection is not None and getattr(connection, "is_open", False):
                try:
                    connection.close()
                except Exception:
                    pass
        log.info("Worker stopped")


def main():
    worker = Worker()

    def handle_signal(signum, _frame):
        log.info("Signal %s received", signum)
        worker.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    worker.run()


if __name__ == "__main__":
    main()
