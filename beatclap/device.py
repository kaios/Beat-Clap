"""Where the game is running. python-for-android sets ANDROID_ARGUMENT for apps it builds."""
import os

ON_ANDROID = "ANDROID_ARGUMENT" in os.environ
