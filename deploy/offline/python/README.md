# Python offline dependencies

This directory is the output location for offline Python dependency bundles used by disconnected deployment hosts.

Generate a bundle on an internet-connected Linux x86_64 Docker host:

```bash
UV_LINUX_BIN=/path/to/uv-0.10.9 bash scripts/build-python-offline-cache.sh
```

The generated archive contains the uv cache for the committed `backend/uv.lock`, Linux x86_64, and Python 3.10. Generated archives, checksums, and extracted caches are intentionally ignored by Git. Transfer the `.tar.gz` and matching `.sha256` file to the deployment host.
