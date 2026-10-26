log warn "Example custom post-install script (custom/mkosi-postinst/example-postinst.sh) running in mkosi post-install phase. This runs after packages are installed."
# Runs *outside* the image chroot after packages are installed.
# The target filesystem is at /buildroot; use 'mkosi-chroot' to run commands inside the chroot environment.

declare -i ENABLE_EXAMPLE_CONTAINERD_MIRRORS=1 # flip to 0 to disable
declare -i ENABLE_EXAMPLE_CA_CERTS=0           # flip to 1 to enable

### Example: configure containerd registry mirrors for a few common registries.
# Each target registry is a directory under /etc/containerd/certs.d with a hosts.toml file.
# You could also do this with individual files and directories in custom/files/ dir.
# The mirror is a zot pull-through cache (plain HTTP, anonymous), serving each upstream under /v2/<registry>.
# The upstream stays as 'server', so pulls fall back to it if the mirror is down.

if [[ ${ENABLE_EXAMPLE_CONTAINERD_MIRRORS} -gt 0 ]]; then

    mirror_base="http://192.168.76.110/v2"
    declare -A registry_upstreams=(
        ["docker.io"]="https://registry-1.docker.io"
        ["ghcr.io"]="https://ghcr.io"
        ["quay.io"]="https://quay.io"
        ["registry.k8s.io"]="https://registry.k8s.io"
        ["gcr.io"]="https://gcr.io"
        ["public.ecr.aws"]="https://public.ecr.aws"
        ["codeberg.org"]="https://codeberg.org"
        ["lscr.io"]="https://lscr.io"
    )

    log info "Configuring containerd registry mirrors..."
    mkdir -pv "${BUILDROOT}/etc/containerd/certs.d"

    for registry in "${!registry_upstreams[@]}"; do
        upstream="${registry_upstreams[$registry]}"
        mirror="${mirror_base}/${registry}"
        log info "Configuring mirror for registry '$registry' pointing to target '$mirror' (fallback '$upstream')"
        mkdir -pv "${BUILDROOT}/etc/containerd/certs.d/${registry}"

        cat <<- ONE_HOSTS_TOML > "${BUILDROOT}/etc/containerd/certs.d/${registry}/hosts.toml"
server = "${upstream}"
[host."${mirror}"]
capabilities = ["pull", "resolve"]
override_path = true
ONE_HOSTS_TOML
    done

    log info "Containerd registry mirrors configuration complete."
fi

### Example: add a custom root CA certificate to the image's trust store.
# You could also do this by dropping .crt files in custom/files/usr/local/share/ca-certificates
if [[ ${ENABLE_EXAMPLE_CA_CERTS} -gt 0 ]]; then

    log info "Adding custom root CA certificate to image trust store..."

    # Debian-family and RPM-family distros keep local CAs in different places, with different tools.
    if [[ "${CAPTAIN_DISTRO_FAMILY}" == "rpm" ]]; then
        ca_dir="${BUILDROOT}/etc/pki/ca-trust/source/anchors"
    else
        ca_dir="${BUILDROOT}/usr/local/share/ca-certificates"
    fi
    mkdir -pv "${ca_dir}"

    curl https://letsencrypt.org/certs/staging/letsencrypt-stg-root-x1.pem \
        -o "${ca_dir}/letsencrypt-stg-root-x1.crt"

    curl https://letsencrypt.org/certs/staging/letsencrypt-stg-root-x2.pem \
        -o "${ca_dir}/letsencrypt-stg-root-x2.crt"

    # update the CA certificate bundle to include the new certs.
    # this is not needed when using .crt files in the custom/files/ directory, since the regular
    # (non-custom) postinst already does this.
    if [[ "${CAPTAIN_DISTRO_FAMILY}" == "rpm" ]]; then
        mkosi-chroot update-ca-trust extract
    else
        mkosi-chroot update-ca-certificates --fresh --verbose
    fi

    log info "Custom root CA certificate added and CA bundle updated."
fi
