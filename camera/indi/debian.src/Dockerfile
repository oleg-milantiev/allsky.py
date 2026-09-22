FROM python:3.12-slim-trixie

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Europe/Moscow

WORKDIR /tmp

# ============================================================
# System dependencies
# ============================================================

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        cmake \
        ninja-build \
        build-essential \
        pkg-config \
        cdbs \
        dkms \
        fxload \
        \
        # D-Bus / dbus-python
        libdbus-1-dev \
        libglib2.0-dev \
        \
        # INDI
        libev-dev \
        libgps-dev \
        libgsl-dev \
        libraw-dev \
        libusb-dev \
        libusb-1.0-0-dev \
        zlib1g-dev \
        libftdi-dev \
        libjpeg-dev \
        libkrb5-dev \
        libnova-dev \
        libtiff-dev \
        libfftw3-dev \
        librtlsdr-dev \
        libcfitsio-dev \
        libgphoto2-dev \
        libdc1394-dev \
        libboost-dev \
        libboost-regex-dev \
        libcurl4-gnutls-dev \
        libtheora-dev \
        libudev-dev \
        liberfa-dev \
        \
        usbutils \
    && \
    rm -rf /var/lib/apt/lists/* && \
python3 -m pip install \
        --no-cache-dir \
        adafruit-circuitpython-bme280 \
        RPi.GPIO \
        adafruit-blinka \
        adafruit-platformdetect \
        zwoasi \
        pika \
        astropy \
        ephem && \
python3 -m pip install \
        --no-cache-dir \
        dbus-python==1.4.0 && \
python3 -c \
    "import dbus; print('dbus:', dbus.__file__)" && \
git clone \
        --depth 1 \
        https://github.com/indilib/indi.git \
        /tmp/indi && \
git clone \
        --depth 1 \
        https://github.com/indilib/indi-3rdparty.git \
        /tmp/indi-3rdparty && \
cmake \
        -S /tmp/indi \
        -B /tmp/indi-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release \
        -DINDI_BUILD_SERVER=ON \
        -DINDI_BUILD_CLIENT=ON \
        -DINDI_BUILD_COMMON=ON \
        -DINDI_BUILD_DRIVERS=OFF \
        -DINDI_BUILD_QT_CLIENT=OFF \
        -DINDI_BUILD_UNITTESTS=OFF \
        -DINDI_BUILD_INTEGTESTS=OFF \
        -DINDI_BUILD_EXAMPLES=OFF \
        -DINDI_BUILD_XISF=OFF \
        -DINDI_INSTALL_UDEV_RULES=ON && \
cmake \
        --build /tmp/indi-build \
        --parallel 4 && \
cmake \
        --install /tmp/indi-build && \
ldconfig && \
command -v indiserver && \
    indiserver 2>&1 | grep -q "INDI Library:" && \
    echo "INDI server installed successfully" && \
cmake \
        -S /tmp/indi-3rdparty/libqhy \
        -B /tmp/libqhy-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release && \
cmake \
        --build /tmp/libqhy-build \
        --parallel 4 && \
cmake \
        --install /tmp/libqhy-build && \
ldconfig && \
cmake \
        -S /tmp/indi-3rdparty/libasi \
        -B /tmp/libasi-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release && \
cmake \
        --build /tmp/libasi-build \
        --parallel 4 && \
cmake \
        --install /tmp/libasi-build && \
ldconfig && \
cmake \
        -S /tmp/indi-3rdparty/indi-sx \
        -B /tmp/indi-sx-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF && \
cmake \
        --build /tmp/indi-sx-build \
        --parallel 4 && \
cmake \
        --install /tmp/indi-sx-build && \
cmake \
        -S /tmp/indi-3rdparty/indi-qhy \
        -B /tmp/indi-qhy-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF && \
cmake \
        --build /tmp/indi-qhy-build \
        --parallel 4 && \
cmake \
        --install /tmp/indi-qhy-build && \
cmake \
        -S /tmp/indi-3rdparty/indi-asi \
        -B /tmp/indi-asi-build \
        -G Ninja \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF && \
cmake \
        --build /tmp/indi-asi-build \
        --parallel 4 && \
cmake \
        --install /tmp/indi-asi-build && \
ldconfig && \
python3 -m pip install \
        --no-cache-dir \
        requests \
        bottle && \
python3 -m pip install \
        --no-cache-dir \
        --only-binary=:all: \
        --no-deps \
        pyindi-client==2.2.0 && \
mkdir -p /tmp/sim-src && \
    cp /tmp/indi/drivers/ccd/sky_renderer.cpp \
       /tmp/indi/drivers/ccd/ccd_simulator.cpp \
       /tmp/sim-src/ && \
    cp /tmp/indi/drivers/ccd/sky_renderer.h \
       /tmp/indi/drivers/ccd/ccd_simulator.h \
       /tmp/sim-src/ && \
    printf '%s\n' \
        'cmake_minimum_required(VERSION 3.16)' \
        'project(indi_simulator_ccd LANGUAGES CXX)' \
        '' \
        'set(CMAKE_MODULE_PATH "/tmp/indi/cmake_modules")' \
        '' \
        'find_package(INDI REQUIRED COMPONENTS driver)' \
        '' \
        'add_executable(indi_simulator_ccd' \
        '    sky_renderer.cpp' \
        '    ccd_simulator.cpp' \
        ')' \
        '' \
        'target_compile_definitions(indi_simulator_ccd PRIVATE' \
        '    USE_EQUATORIAL_PE' \
        ')' \
        '' \
        'target_include_directories(indi_simulator_ccd PRIVATE' \
        '    ${INDI_INCLUDE_DIR}' \
        '    /tmp/indi/libs' \
        ')' \
        '' \
        'target_link_libraries(indi_simulator_ccd PRIVATE' \
        '    ${INDI_DRIVER_LIBRARIES}' \
        '    nova' \
        '    cfitsio' \
        ')' \
        '' \
        'install(TARGETS indi_simulator_ccd RUNTIME DESTINATION bin)' \
        > /tmp/sim-src/CMakeLists.txt && \
    cmake \
        -S /tmp/sim-src \
        -B /tmp/sim-build \
        -G Ninja \
        -DCMAKE_BUILD_TYPE=Release && \
    cmake --build /tmp/sim-build -j"$(nproc)" && \
    cmake --install /tmp/sim-build && \
python3 -c \
    "import PyIndi; print('PyIndi:', PyIndi.__file__)" && \
echo "=== INDI drivers ===" && \
    find /usr/bin \
        -maxdepth 1 \
        -type f \
        -name 'indi_*' \
        -print | sort && \
echo "=== INDI libraries ===" && \
    ldconfig -p | grep -E 'libindi|libqhy|libASICamera' || true && \
python3 -c \
    "import dbus, PyIndi; \
     print('D-Bus:', dbus.__file__); \
     print('PyIndi:', PyIndi.__file__); \
     print('INDI Python client OK')" && \
rm -rf \
        /tmp/sim-src \
        /tmp/indi \
        /tmp/indi-3rdparty \
        /tmp/indi-build \
        /tmp/libqhy-build \
        /tmp/libasi-build \
        /tmp/indi-sx-build \
        /tmp/indi-qhy-build \
        /tmp/indi-asi-build

WORKDIR /camera
