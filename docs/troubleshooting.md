# Troubleshooting

---

## Permission denied when browsing an external drive

**Symptom:** Clicking into a USB or HDD in the folder browser shows "Permission denied."

**Cause:** The drive was auto-mounted by the OS as `root`-owned with restrictive permissions (`drwx------`), so only root can read it.

**Diagnosis:** Check ownership and permissions of the mount point:

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
# Find the device node
lsblk

# Remount with your user's UID/GID
sudo umount /media/$USER/<drive-name>
sudo mount -o uid=$(id -u),gid=$(id -g) /dev/sdXN /media/$USER/<drive-name>
```

Replace `/dev/sdXN` with the actual device shown by `lsblk`.

---

## External drive not appearing in the device picker

**Symptom:** The "Browse…" device list is empty or missing a connected drive.

**Steps:**

1. Confirm the drive is mounted: `lsblk -o NAME,MOUNTPOINT,FSTYPE,SIZE`
2. The app looks for devices in these locations:
   - `/media/<user>/<volume>`
   - `/run/media/<user>/<volume>`
   - Any `/dev/sd*`, `/dev/nvme*`, `/dev/mmcblk*` mount in `/proc/mounts` that is not a system partition
3. If the drive is mounted elsewhere (e.g. `/mnt/mydrive`), type the path directly into the folder path text box instead of using the browser.

---

## App running inside the dev container cannot see external drives

**Symptom:** Device picker is empty even though drives are mounted on the host.

**Cause:** The dev container creates `/media`, `/mnt`, and `/run/media` as empty directories at build time — host mount points are not automatically forwarded.

**Fix:** Add a bind mount in `.devcontainer/docker-compose.yml`:

```yaml
volumes:
  - /media:/media:ro          # or rw if you need write access
  - /run/media:/run/media:ro
```

Then rebuild the container (`Dev Containers: Rebuild Container` in VS Code).

---

## Corrupted images are silently skipped

**Symptom:** Fewer images than expected appear after loading a folder.

The scanner forces a full pixel decode (`img.load()`) to catch truncated files. Corrupted images are counted and shown as a warning in the sidebar after loading. They are not displayed.
