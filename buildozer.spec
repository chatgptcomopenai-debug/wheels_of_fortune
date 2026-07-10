[app]

# (str) Title of your application
title = Колесо Фортуны

# (str) Package name
package.name = wheeloffortune

# (str) Package domain (needed for android packaging)
package.domain = org.fortune

# (str) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,wav

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,pygame-ce

# (str) Supported orientations
# Valid values are: landscape, portrait, portrait-upside-down, landscape-left, landscape-right
orientation = landscape

# (bool) Use fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Android SDK directory (if empty, it will be automatically downloaded)
android.sdk_path =

# (str) Android NDK directory (if empty, it will be automatically downloaded)
android.ndk_path =

# (bool) Use --private data directory (True) or public (False)
android.private_storage = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
