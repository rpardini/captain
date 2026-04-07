# Builder container for CaptainOS using mkosi
# Encapsulates all mkosi dependencies for reproducible builds.
# Includes skopeo and buildah for OCI image manipulation, and uv for Python tool management.
FROM debian:trixie

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive BUILDAH_ISOLATION=chroot FORCE_COLOR=1

# Add foreign architecture for cross-compilation (arm64 on amd64 and vice versa) and apt-update
# Immediately install the cross-arch grub dependencies
RUN <<-FRAGMENT_WITH_VARIABLES
# Determine arch/cross-arch and install grub and other basic packages (around 200mb layer)
NATIVE_ARCH="$(dpkg --print-architecture)"
FOREIGN_ARCH=$([ "$NATIVE_ARCH" = "amd64" ] && echo "arm64" || echo "amd64")
dpkg --add-architecture "$FOREIGN_ARCH"
apt-get -o "Dpkg::Use-Pty=0" update
apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    "grub-efi-${NATIVE_ARCH}-bin" \
    "grub-efi-${FOREIGN_ARCH}-bin:${FOREIGN_ARCH}" \
    grub-common \
    apt \
    dpkg \
    debian-archive-keyring \
    ubuntu-keyring \
    cpio \
    zstd \
    xz-utils \
    kmod \
    systemd-container \
    systemd \
    udev \
    squashfs-tools \
    mtools \
    erofs-utils \
    dosfstools \
    e2fsprogs \
    btrfs-progs \
    tree
FRAGMENT_WITH_VARIABLES

# Cross-architecture support (arm64 on x86_64 and vice versa) - huge single package
RUN <<-QEMU_USER_FRAGMENT
# Install qemu-user but then delete all un-needed qemu binaries to save space (we only need aarch64 and x86_64)
apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends qemu-user
echo 'All qemus: '
ls -lah /usr/bin/qemu-*
# keep only qemu binary for the arches we're interested in: aarch64 and x86_64
echo 'To be deleted: '
find /usr/bin -name 'qemu-*' -not -name 'qemu-aarch64' -not -name 'qemu-x86_64' -not -name 'qemu-arm*' -not -name 'qemu-amd*' -print0 | xargs -0 ls -lah
echo 'Deleting: '
find /usr/bin -name 'qemu-*' -not -name 'qemu-aarch64' -not -name 'qemu-x86_64' -not -name 'qemu-arm*' -not -name 'qemu-amd*' -print0 | xargs -0 rm -fv
echo 'Remaining: '
ls -lah /usr/bin/qemu-*

QEMU_USER_FRAGMENT

# Extra kernel build tools
RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    make \
    flex \
    bison \
    bc \
    libelf-dev \
    libssl-dev \
    dpkg-dev \
    dwarves \
    pahole

# Those are pulled by build-essential (cross...), but are quite big; pull them ealier to balance layer size
RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    binutils-common \
    libasan8 \
    liblsan0 \
    libubsan1 \
    libhwasan0 \
    binutils-x86-64-linux-gnu \
    libasan8-amd64-cross \
    liblsan0-amd64-cross \
    libtsan2-amd64-cross \
    libc6-amd64-cross \
    linux-libc-dev-amd64-cross \
    libc6-dev-amd64-cross

RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    rsync \
    coreutils \
    git \
    curl \
    ca-certificates \
    qemu-user-static

# Then both, of which one will already be fulfilled
RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends crossbuild-essential-arm64
RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends crossbuild-essential-amd64

# Buildah and Skopeo
# Binary compression
# ISO image creation
# Kernel build deps: build-essential
RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    build-essential \
    containernetworking-plugins \
    bubblewrap \
    skopeo \
    upx-ucl \
    xorriso

RUN apt-get -o "Dpkg::Use-Pty=0" install -y --no-install-recommends \
    buildah

RUN <<-CONFIG_FRAG
## A few small config fragments to make life easier
# git: Ignore owner mismatches in /work, which will be bind-mounted from the host
git config --global --add safe.directory /work \
# buildah: Configure rootless storage driver and chroot isolation (no user-namespace required — we only assemble scratch images, never RUN anything inside them).
printf '[storage]\ndriver = "vfs"\nrunroot = "/var/tmp/buildah-runroot"\ngraphroot = "/var/tmp/buildah-storage"\n' > /etc/containers/storage.conf
# Buildah 1.39+ on Debian requires netavark but we never need networking
# (all images are FROM scratch with no RUN steps).  A no-op stub satisfies
# the startup check.
mkdir -p /usr/libexec/podman
printf '#!/bin/sh\nexit 0\n' > /usr/libexec/podman/netavark
chmod +x /usr/libexec/podman/netavark
CONFIG_FRAG

# Install astral-sh's uv with a script - install to /usr for global access
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/bin" sh && uv --version

# Install mkosi from GitHub (not on PyPI) via uv; symlink to /usr/bin for global access
ARG MKOSI_VERSION=v26
RUN uv tool install "git+https://github.com/systemd/mkosi.git@${MKOSI_VERSION}" && ln -sf ~/.local/bin/mkosi /usr/bin/mkosi && mkosi --version

# Prime uv's cache with our pyproject.toml to speed up runtime
COPY pyproject.toml /tmp/pyproject.toml
COPY captain /tmp/captain
COPY build.py /tmp/build.py
WORKDIR /tmp
RUN uv --verbose run captain --version

WORKDIR /work
