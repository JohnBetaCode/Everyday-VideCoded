# Troubleshooting

---

## Dev container fails to start — Wayland socket mount error

**Symptom:**

```
Error response from daemon: ... error mounting "/run/user/1000/wayland-0" to rootfs ...
mount src=/run/user/1000/wayland-0 ... not a directory
```

**Cause:** VS Code's Remote Containers extension auto-forwards the Wayland display socket into the container. If a previous failed mount attempt left a *directory* at `/run/user/1000/wayland-0` instead of a socket file, Docker can't bind-mount it.

**Fix:**

```bash
sudo rm -rf /run/user/1000/wayland-0
```

If you are in an active Wayland session, log out and back in so the compositor recreates the socket. Then reconnect the dev container.

---

## Permission denied writing to `~/.u2net` (rembg model download fails)

**Symptom:**

```
Pipeline error: [Errno 13] Permission denied: '/home/ada/.u2net/tmp...'
Pooch could not write to data cache folder '/home/ada/.u2net'.
```

**Cause:** The `u2net-cache` Docker volume was initialised with root ownership before the `chown` fix was applied to the Dockerfile.

**Fix:** Delete the stale volume and rebuild so Docker re-initialises it with the correct `ada` ownership:

```bash
docker volume rm devcontainer_u2net-cache
```

Then **Rebuild Container** in VS Code.

---

## `libcublasLt.so.12` not found — CUDA provider fails to load

**Symptom:**

```
[E:onnxruntime] Failed to load library libonnxruntime_providers_cuda.so
libcublasLt.so.12: cannot open shared object file: No such file or directory
```

**Cause:** The old `python:3.12-slim` base image has no CUDA libraries. `onnxruntime-gpu` (installed by `rembg[gpu]`) needs `libcublasLt` from the CUDA runtime.

**Fix:** The Dockerfile now uses `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04` as its base image, which ships the required CUDA and cuBLAS libraries. Rebuild the container.

To verify GPU is active after rebuilding:

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
# Should include CUDAExecutionProvider
```

---

## `libGL.so.1` not found — mediapipe / OpenCV fails to import

**Symptom:**

```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
  File "...mediapipe/tasks/python/vision/drawing_utils.py"
  import cv2
```

**Cause:** `mediapipe` depends on `opencv-python`, which requires the system OpenGL library (`libGL.so.1`) and GLib (`libglib2.0-0`). These are not present in the CUDA runtime image by default.

**Fix:** Both packages are now installed in the Dockerfile:

```dockerfile
apt-get install -y libgl1 libglib2.0-0
```

Rebuild the container.

---

## GPU not used by rembg (blur background runs slow)

**Symptom:** Background blur works but is very slow (~3–5s per image).

**Check which providers are active:**

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

- `CUDAExecutionProvider` in the list → GPU is active.
- Only `CPUExecutionProvider` → GPU is not available or not configured.

**Cause A — No NVIDIA GPU on the machine:**
Remove the `deploy` block from `.devcontainer/docker-compose.yml` — everything works on CPU, just slower.

**Cause B — nvidia-container-toolkit not installed on the host:**

```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Then rebuild the container.

**Cause C — rembg model not yet downloaded:**
The first call to "Blur background" downloads the U2Net model (~170 MB) to `~/.u2net/` inside the container. It is stored in a named Docker volume (`u2net-cache`) and persists across rebuilds. Subsequent calls are fast.

---

## Permission denied when browsing an external drive

**Symptom:** Clicking into a USB or HDD in the folder browser shows "Permission denied."

**Cause:** The drive was auto-mounted by the OS as `root`-owned with restrictive permissions (`drwx------`), so only root can read it.

**Diagnosis:**

```bash
ls -la /media/$USER/
stat /media/$USER/<drive-name>
```

If `Uid` is `0 / root` and permissions are `0700`, that's the problem.

**Fix — ext4 / Linux-native filesystems:**

```bash
sudo chmod 755 /media/$USER/<drive-name>
```

**Fix — NTFS / exFAT / FAT32 (ownership is set at mount time):**

```bash
lsblk
sudo umount /media/$USER/<drive-name>
sudo mount -o uid=$(id -u),gid=$(id -g) /dev/sdXN /media/$USER/<drive-name>
```

Replace `/dev/sdXN` with the actual device shown by `lsblk`.

---

## External drive not appearing in the device picker

**Symptom:** The "Browse…" device list is empty or missing a connected drive.

**Steps:**

1. Confirm the drive is mounted: `lsblk -o NAME,MOUNTPOINT,FSTYPE,SIZE`
2. The app looks for devices in:
   - `/media/<user>/<volume>`
   - `/run/media/<user>/<volume>`
   - Any `/dev/sd*`, `/dev/nvme*`, `/dev/mmcblk*` mount in `/proc/mounts` that is not a system partition
3. If the drive is mounted elsewhere (e.g. `/mnt/mydrive`), type the path directly into the folder path text box.

---

## App running inside the dev container cannot see external drives

**Symptom:** Device picker is empty even though drives are mounted on the host.

**Cause:** The dev container creates `/media`, `/mnt`, and `/run/media` as empty directories — host mount points are not automatically forwarded.

**Fix:** Bind mounts are already configured in `.devcontainer/docker-compose.yml`:

```yaml
volumes:
  - /media:/media:ro
  - /run/media:/run/media:ro
  - /mnt:/mnt:ro
```

If they are missing, add them and rebuild (`Dev Containers: Rebuild Container`).

---

## Corrupted images are silently skipped

**Symptom:** Fewer images than expected appear after loading a folder.

The scanner forces a full pixel decode (`img.load()`) to catch truncated files. Corrupted images are counted and shown as a warning in the sidebar after loading. They are not displayed.
