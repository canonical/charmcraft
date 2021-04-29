import site
import os

snap_dir = os.getenv("SNAP")
if snap_dir:
  site.ENABLE_USER_SITE = False
  site.addsitedir(os.path.join(snap_dir, "lib"))
  site.addsitedir(os.path.join(snap_dir, "usr/lib/python3/dist-packages"))
