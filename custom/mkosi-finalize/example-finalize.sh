log warn "Example custom finalize script (custom/mkosi-finalize/example-finalize.sh) running in mkosi finalize phase. This runs after the image is built and before it is packaged."
# Keep in mind that the target filesystem is at /buildroot at this stage, and commands ran here are all powerful ref the host system.
