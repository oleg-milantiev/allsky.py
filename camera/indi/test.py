#!/usr/bin/env python3
import PyIndi
import time
import os
import io
import threading
from pathlib import Path

from astropy.io import fits

INDI_HOST = os.getenv("INDI_HOST", "indi")
INDI_PORT = int(os.getenv("INDI_PORT", "7624"))
INDI_CAMERA_NAME = os.getenv("INDI_CAMERA_NAME", "").strip()
INDI_BLOB_PROPERTY = os.getenv("INDI_BLOB_PROPERTY", "CCD1")
FITS_PATH = Path(os.getenv("FITS_PATH", "/fits/test.fit"))
TELESCOPE_NAME = os.getenv("TELESCOPE_NAME", "AllSky")

os.system('python3 /common/udev.py')


def _property_state(prop):
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
                return state_names.get(method(), str(method()).upper())
            except Exception:
                pass
    return None


def _number_value(prop):
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


class TestClient(PyIndi.BaseClient):
    def __init__(self):
        super().__init__()
        self.camera = None
        self._blob_lock = threading.Lock()
        self._blob_data = None
        self._blob_format = None
        self._accept_blob = False
        self.captured = threading.Event()
        self._exposure_state = None
        self._exposure_value = None
        self._commanded_exposure = None
        self._command_time = None

    def newDevice(self, device):
        print(f"[newDevice] {device.getDeviceName()}")

    def removeDevice(self, device):
        print(f"[removeDevice] {device.getDeviceName()}")

    def newProperty(self, prop):
        if prop.getName() in ("CCD_EXPOSURE", INDI_BLOB_PROPERTY):
            print(f"  newProperty: {prop.getDeviceName()}/{prop.getName()}")

    def removeProperty(self, prop):
        print(f"[removeProperty] {prop.getDeviceName()}/{prop.getName()}")

    def updateProperty(self, prop):
        try:
            if self.camera is None:
                return
            if prop.getDeviceName() != self.camera.getDeviceName():
                return

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
                raw = blob.getBlob()
            if raw is None:
                return

            self._store_blob(bytes(raw), blob.getFormat(), blob_property.getName(), "updateProperty")
        except Exception:
            print(f"[updateProperty error] {e}")

    def _log_exposure_update(self, prop):
        state = _property_state(prop)
        value = _number_value(prop)
        now = time.monotonic()

        if state is not None and state != self._exposure_state:
            elapsed = now - self._command_time if self._command_time else None
            if elapsed is not None and self._commanded_exposure:
                print(f"[CCD_EXPOSURE] {self._exposure_state} -> {state}, value={value:.6f}, "
                      f"{elapsed:.3f}s since command (requested={self._commanded_exposure:.6f}s)")
            else:
                print(f"[CCD_EXPOSURE] {self._exposure_state} -> {state}, value={value}")

        if (state == "BUSY" and self._exposure_state == "BUSY"
                and value is not None and self._exposure_value is not None
                and value > self._exposure_value + max(0.25, (self._commanded_exposure or 0) * 0.10)):
            print(f"[CCD_EXPOSURE WARN] remaining time increased while BUSY: "
                  f"{self._exposure_value:.3f}s -> {value:.3f}s")

        self._exposure_state = state
        self._exposure_value = value

    def _store_blob(self, data, blob_format, blob_name, source):
        if not data:
            return
        with self._blob_lock:
            if not self._accept_blob:
                print(f"[BLOB] ignoring outside capture: {source}/{blob_name}/{len(data)}")
                return
            if self._blob_data is not None:
                print(f"[BLOB] ignoring duplicate: {source}/{blob_name}/{len(data)}")
                return
            self._blob_data = data
            self._blob_format = blob_format
            self._accept_blob = False
            self.captured.set()
        print(f"[BLOB] captured: {source} {blob_name} {len(data)} bytes format={blob_format}")

    def newBlob(self, bp):
        try:
            blob_name = bp.getName()
            blob_len = int(bp.getBlobLen())
            print(f"[newBlob] {blob_name} {blob_len} bytes")
            if blob_len > 0:
                data = bp.getBlob()
                if data is None:
                    data = bp.getblobdata()
                if data is not None:
                    self._store_blob(bytes(data), bp.getFormat(), blob_name, "newBlob")
        except Exception as e:
            print(f"[newBlob error] {e}")

    def newBLOB(self, bp):
        try:
            for blob in bp:
                self._store_blob(bytes(blob.getblobdata() or blob.getBlob()), blob.getFormat(), blob.getName(), "newBLOB")
        except TypeError:
            try:
                data = bp.getBlob() or bp.getblobdata()
                if data:
                    self._store_blob(bytes(data), bp.getFormat(), bp.getName(), "newBLOB")
            except Exception as e:
                print(f"[newBLOB error] {e}")
        except Exception as e:
            print(f"[newBLOB error] {e}")

    def newBlobDone(self, bp, blob_file):
        print(f"[newBlobDone] {blob_file}")

    def newMessage(self, device, message_id):
        try:
            msg = device.messageQueue(message_id)
            print(f"[message] {device.getDeviceName()} [{message_id}]: {msg}")
        except Exception:
            pass

    def prepare_for_blob(self):
        with self._blob_lock:
            self._blob_data = None
            self._blob_format = None
            self._accept_blob = True
        self.captured.clear()

    def cancel_blob_wait(self):
        with self._blob_lock:
            self._accept_blob = False

    def mark_exposure(self, exposure):
        self._commanded_exposure = float(exposure)
        self._command_time = time.monotonic()
        self._exposure_value = None


def _wait_until_idle(camera, timeout=10):
    deadline = time.monotonic() + timeout
    last_state = None
    while time.monotonic() < deadline:
        prop = camera.getNumber("CCD_EXPOSURE")
        if prop is None:
            raise RuntimeError("CCD_EXPOSURE disappeared")
        state = _property_state(prop)
        if state != last_state and state:
            print(f"[idle] CCD_EXPOSURE state={state}")
            last_state = state
        if state != "BUSY":
            return
        time.sleep(0.1)
    raise TimeoutError(f"Camera BUSY for {timeout}s")


def main():
    INDI_HOST = os.getenv("INDI_HOST", "indi")
    INDI_PORT = int(os.getenv("INDI_PORT", "7624"))

    client = TestClient()
    client.setServer(INDI_HOST, INDI_PORT)

    print("\n--- Connecting to INDI ---")
    connected = client.connectServer()
    print(f"  Connected: {connected}")
    if not connected:
        print("FAILED to connect")
        os._exit(1)

    print("\n--- Waiting for devices ---")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        devices = list(client.getDevices())
        if devices:
            for d in devices:
                print(f"  {d.getDeviceName()}")
            break
        time.sleep(1)

    time.sleep(2)

    # Find camera
    print("\n--- Selecting camera ---")
    all_devices = list(client.getDevices())
    print(f"  Available: {[d.getDeviceName() for d in all_devices]}")
    camera = None

    if INDI_CAMERA_NAME:
        for d in all_devices:
            if d.getDeviceName() == INDI_CAMERA_NAME:
                camera = d
                break
        if not camera:
            print(f"  {INDI_CAMERA_NAME!r} not found, trying first available device")

    if not camera:
        for d in all_devices:
            if any(k in d.getDeviceName() for k in ("ZWO", "ASI", "Atik", "SBIG", "SX", "Simulator")):
                camera = d
                break
    if not camera and all_devices:
        camera = all_devices[0]
    if not camera:
        print("No camera device!")
        os._exit(1)

    camera_name = camera.getDeviceName()
    client.camera = camera
    print(f"  Selected: {camera_name}")
    time.sleep(2)

    # Connect camera (simulator may already be connected)
    print("\n--- Connecting camera ---")
    conn_prop = camera.getProperty("CONNECTION")
    if conn_prop is not None and not camera.isConnected():
        sw = conn_prop.getSwitch()
        for el in sw:
            el.setState(1 if el.getName() == "CONNECT" else 0)
        client.sendNewSwitch(conn_prop)
        print("  sent CONNECTION=Connect")

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not camera.isConnected():
            time.sleep(0.1)
        if not camera.isConnected():
            print("  FAILED: camera not connected")
            os._exit(1)
    elif camera.isConnected():
        print("  Already connected")
    else:
        print("  No CONNECTION property, skipping")
    time.sleep(2)

    # Wait for properties
    print("\n--- Waiting for required properties ---")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        exposure = camera.getNumber("CCD_EXPOSURE")
        blob = camera.getBLOB(INDI_BLOB_PROPERTY)
        if exposure is not None and blob is not None:
            print("  CCD_EXPOSURE and CCD_BLOB received")
            break
        time.sleep(0.1)
    else:
        print("  FAILED: required properties not received")
        os._exit(1)

    # Enable BLOB
    print("\n--- Enabling BLOB ---")
    client.setBLOBMode(PyIndi.B_ALSO, camera_name, INDI_BLOB_PROPERTY)
    print(f"  B_ALSO set for {INDI_BLOB_PROPERTY}")
    time.sleep(1)

    # Set gain
    print("\n--- Gain ---")
    gain_prop = camera.getNumber("CCD_GAIN")
    if gain_prop is not None:
        if len(gain_prop) == 1:
            elem = gain_prop[0]
        else:
            matching = [e for e in gain_prop if e.getName() in ("GAIN", "CCD_GAIN_VALUE")]
            if len(matching) == 1:
                elem = matching[0]
            else:
                print(f"  Multiple gain widgets, using first")
                elem = gain_prop[0]
        elem.setValue(10)
        client.sendNewNumber(gain_prop)
        print(f"  Gain set to 10")
    time.sleep(1)

    # Set binning 2x2
    print("\n--- Binning ---")
    bin_prop = camera.getNumber("CCD_BINNING")
    if bin_prop is not None:
        bin_prop[0].setValue(2)
        bin_prop[1].setValue(2)
        client.sendNewNumber(bin_prop)
        print("  Binning set to 2x2 (HOR=2, VER=2)")
    time.sleep(1)

    # Exposure
    print("\n--- Exposure ---")
    exp_time = float(os.getenv("EXPOSURE", "1.0"))
    exposure_prop = camera.getNumber("CCD_EXPOSURE")
    if exposure_prop is None:
        print("  No CCD_EXPOSURE property")
        os._exit(1)

    print(f"  CCD_EXPOSURE: min={exposure_prop[0].getMin()} max={exposure_prop[0].getMax()} "
          f"step={exposure_prop[0].getStep()}")

    with client._exposure_lock if hasattr(client, '_exposure_lock') else threading.Lock():
        _wait_until_idle(camera)
        client.prepare_for_blob()
        _set_number_value(exposure_prop, "CCD_EXPOSURE_VALUE", exp_time)
        client.mark_exposure(exp_time)

        print(f"  Setting exposure={exp_time}s")
        started = time.monotonic()
        client.sendNewNumber(exposure_prop)
        print(f"  sendNewNumber sent")

        timeout = max(30.0, exp_time * 3.0 + 10.0)
        print(f"\n--- Waiting for BLOB (timeout={timeout:.1f}s) ---")
        if client.captured.wait(timeout=timeout):
            if client._blob_data:
                data = client._blob_data
                blob_format = client._blob_format
                elapsed = time.monotonic() - started
                print(f"\nSUCCESS! {len(data)} bytes format={blob_format} elapsed={elapsed:.3f}s")

                # Validate FITS
                if data[:9] == b"SIMPLE  =":
                    print("  Valid FITS header")
                else:
                    print(f"  WARNING: not FITS: {data[:32]!r}")

                # Save with proper FITS header
                FITS_PATH.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = FITS_PATH.with_name(FITS_PATH.name + ".tmp")
                with fits.open(io.BytesIO(data), mode="readonly") as src:
                    output = fits.HDUList([hdu.copy() for hdu in src])
                    try:
                        output[0].header["TELESCOP"] = (TELESCOPE_NAME, "Telescope / camera")
                        from datetime import datetime, timezone
                        output[0].header["DATE-OBS"] = (
                            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                            "Observation timestamp"
                        )
                        output[0].header["EXPTIME"] = (float(exp_time), "Exposure time (s)")
                        output.writeto(tmp_path, overwrite=True)
                    finally:
                        output.close()
                os.replace(tmp_path, FITS_PATH)
                print(f"  Saved to {FITS_PATH}")
            else:
                print("FAILED: no data")
                os._exit(1)
        else:
            print(f"FAILED: timeout {timeout:.1f}s")
            client.cancel_blob_wait()
            os._exit(1)

    client.camera = None


if __name__ == "__main__":
    main()
