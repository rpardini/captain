# CaptainOS

A minimal, systemd-based in-memory OS for [Tinkerbell](https://tinkerbell.org) bare-metal provisioning. Unrelated change.

CaptainOS boots via PXE/iPXE, runs entirely from RAM as a compressed CPIO initramfs, and provides a container runtime
environment for the [tink-agent](https://github.com/tinkerbell/tinkerbell) — the component that drives hardware
provisioning workflows.

## Why does CaptainOS exist?

CaptainOS is the next generation of Tinkerbell's in-memory OS, building on years of experience building, maintaining,
and operating [HookOS](https://github.com/tinkerbell/hook) in production.
It is built with [mkosi](https://github.com/systemd/mkosi), producing a minimal systemd-based Debian OS that runs
entirely from RAM.

- **Significantly smaller initramfs** — small enough to boot comfortably on resource-constrained single-board computers.
- **No Docker-in-Docker** — tink-agent runs directly on the host with containerd, giving it native access to the
  container runtime without any nesting.
- **Familiar operations** — systemd foundation with journalctl, networkd, and standard service management make debugging
  and troubleshooting straightforward.
- **Simpler architecture** — fewer layers between hardware and workload, easier to develop against and extend.

## How it works

1. The machine PXE boots the kernel (`vmlinuz`) and initramfs (`initramfs`) or runs the UEFI-bootable ISO image
2. A custom `/init` script transitions the rootfs to tmpfs, then exec's systemd
3. systemd-networkd configures DHCP on all ethernet interfaces
4. containerd starts, then `tink-agent-setup` pulls the tink-agent container image (configured via kernel cmdline),
   extracts the binary, and runs it as a host process
5. tink-agent connects to the Tinkerbell server and executes provisioning workflows

## Build model

The current CLI is click-based (`captain`) with flavor-driven image generation.

- `captain build` runs: **tools -> initramfs (mkosi) -> iso (if flavor supports it) -> collect artifacts**
- `captain kernel` is a separate stage used when building kernel artifacts directly (for example `trixie-slim`
  workflows)
- Flavor templates and static overlays are rendered into generated `mkosi.*` files
- `mkosi.output/` keeps hashed per-flavor build outputs; `out/` gets stable publishable filenames

## Build system Usage

**Prerequisites:** `uv` (Python), Docker (with buildx/BuildKit).

- On Debian, the regular Debian-supplied `docker.io` and `docker-cli`/`docker-buildx` packages work fine. You can also
  use Docker CE from Docker Inc if you prefer.
- On MacOS with brew, `colima` is a good alternative to Docker Desktop or similar.

```bash
# Install Astral's `uv` if you don't have it: https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh # then re-log in

# top-level help
uv run captain --help
```

### Core commands

**Important**: please pay attention to the level flags are defined. For example, `--flavor-id` is a global option and
needs to be passed after `uv run captain` but before the subcommand (`build`, `kernel`, etc).
We're investigating ways to make this more flexible using Python's Click library, but for now please follow the
documented usage.

```bash
uv run captain builder --help
uv run captain build --help
uv run captain kernel --help
uv run captain tools --help
uv run captain iso --help
uv run captain qemu --help
uv run captain release --help
uv run captain shell --help
```

## Flavors

Available flavors are discovered dynamically from `captain/flavors/`. Here is a current list:

| Flavor                     | Architectures    | ISO | Description                                                                                                           |
|----------------------------|------------------|-----|-----------------------------------------------------------------------------------------------------------------------|
| `trixie-full`              | `amd64`, `arm64` | yes | Debian Trixie, standard Debian linux-generic kernel, working `apt` package manager                                    |
| `trixie-slim`              | `amd64`, `arm64` | yes | Kernel built from source, slimmed down Debian userspace, ACPI/UEFI only                                               |
| `trixie-armbian-rpi`       | `arm64`          | no  | For RaspberryPi's, using Armbian's bcm2711 kernel; produces `rpi-firmware` which is ready-to-netboot on RPi's         |
| `trixie-meson64`           | `arm64`          | no  | For Amlogic boards, using Armbian's meson64 kernel                                                                    |
| `trixie-rockchip64`        | `arm64`          | no  | For Rockchip boards (rk35xx, rk33xx, etc) using Armbian's _mainline_ rockchip64 kernel                                |
| `trixie-rockchip64-vendor` | `arm64`          | no  | For Rockchip boards (rk35xx) using the Rockchip vendor kernel from Armbian. Prefer the non-vendor flavor if possible. |
| `trixie-genio`             | `arm64`          | no  | For MediaTek Genioboards, using Armbian's genio kernel                                                                |

Use `--flavor-id` (or environment `FLAVOR_ID`) to select one.

## Build modes

Most stages support `docker | native | skip`:

- `--tools-mode` / `TOOLS_MODE`
- `--mkosi-mode` / `MKOSI_MODE`
- `--iso-mode` / `ISO_MODE`
- `--kernel-mode` / `KERNEL_MODE`
- `captain release --release-mode` / `RELEASE_MODE`

Defaults are command-specific (for example, `captain build` defaults to `--tools-mode native`, while `captain tools`
defaults to `--tools-mode docker`). Use `--help` on each command for current defaults.

## Customization via `custom/`

The `custom/` directory is mounted automatically in docker-mode runs and applied by Debian-based flavors.

- `custom/packages.txt`: one package per line (comments allowed)
- `custom/files/`: copied into the image (mapped under `mkosi.extra/`)
- `custom/mkosi-postinst/`: appended scripts for post-install phase
- `custom/mkosi-finalize/`: appended scripts for finalize phase

See examples under `custom/` in this repository.

## Output artifacts

Final artifacts are copied to `out/` with flavor-aware names:

- `out/vmlinuz-<flavor-id>-<arch>`
- `out/initramfs-<flavor-id>-<arch>`
- `out/captainos-<flavor-id>-<arch>.iso` (only for ISO-capable flavors)
- `out/dtb-<flavor-id>-<arch>/` (directory, arm64 flavors that export DTBs)

`<arch>` uses Linux output architecture names (`x86_64`, `aarch64`).

## Release (OCI artifacts)

Release operations are grouped under `captain release`:

```bash
# publish
uv run captain release --target amd64 publish

# pull artifacts into out/release/
uv run captain release --target combined pull --pull-output release

# retag existing images
uv run captain release --src-tag v0.0.0-abcdef1-trixie-full tag --new-tag v1.0.0
```

Notes:

- Base source tag defaults to `v0.0.0-<sha7>-<flavor-id>`.
- Per-arch publish refs append `-amd64` or `-arm64`; combined uses the bare source tag.
- `publish` computes `sha256sums-<flavor-id>-<arch>.txt` and includes checksums as OCI layers.
- `REGISTRY_INSECURE=1` can be used for insecure registries (propagated to buildah/skopeo wrappers).

For the rationale behind the Buildah + Skopeo approach, see `docs/design-decisions/oci-tooling-buildah-skopeo.md`.

## Testing with QEMU

`captain qemu` boots artifacts from `out/` and forwards additional arguments to the kernel cmdline.

```bash
# boot with defaults
uv run captain --arch amd64 --flavor-id trixie-full qemu

# pass extra kernel cmdline args after --
uv run captain --arch amd64 --flavor-id trixie-full qemu -- tink_worker_image=ghcr.io/tinkerbell/tink-agent:latest
```

You will need OVMF firmware for the architecture installed on the host system:

- On MacOS with brew, OVMF builds for both x86 and arm64 is included with the `qemu` package.
- On Linux, you can install `ovmf` from your package manager:
    - Debian: x86: `ovmf`, arm64: `qemu-efi-aarch64`
    - Fedora: `edk2-ovmf` (both architectures)

On native-host architecture runs, acceleration is enabled when available (`hvf` on macOS, `kvm` on Linux).

Exit QEMU with `Ctrl-a x` (that's `Ctrl` + `a`, release, then press `x`).

## Project layout

```text
.
|- build.py
|- captain/
|  |- cli/                    # click CLI groups/commands
|  |- flavors/                # flavor definitions and mkosi overlays
|  |- oci/                    # OCI publish/pull/tag logic
|  |- artifacts.py            # copy outputs into out/
|  |- docker.py               # builder image + docker relaunch helpers
|  |- iso.py                  # ISO assembly
|  |- kernel.py               # kernel build logic
|  |- qemu.py                 # qemu launcher
|  `- tools.py                # pinned tool downloads
|- custom/                    # user customizations
|- docs/                      # documentation
|- kernel.configs/            # kernel configuration (defconfig) for trixie-slim kernel builds
|- mkosi.input/               # build inputs (generated and cached)
|- mkosi.output/              # per-flavor hashed mkosi outputs
`- out/                       # final artifacts for release/use
```

## License

See [Tinkerbell](https://github.com/tinkerbell/captain/blob/main/LICENSE) for license information.
