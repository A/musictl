#!/usr/bin/env python3
import re
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import dbus


class Mpris:
    """Handles MPRIS interactions with media players."""

    def __init__(self):
        pass

    def _dbus_to_python(self, data):
        """Convert dbus data types to python native data types."""
        if isinstance(data, dbus.String):
            data = str(data)
        elif isinstance(data, dbus.Boolean):
            data = bool(data)
        elif isinstance(data, dbus.Int64):
            data = int(data)
        elif isinstance(data, dbus.Double):
            data = float(data)
        elif isinstance(data, dbus.Array):
            data = [self._dbus_to_python(value) for value in data]
        elif isinstance(data, dbus.Dictionary):
            new_data = dict()
            for key in data.keys():
                new_data[self._dbus_to_python(key)] = self._dbus_to_python(data[key])
            data = new_data
        return data

    def get_current_track(self, player_command: str) -> Optional[Path]:
        """Get currently playing track file path."""
        try:
            bus = dbus.SessionBus()

            for service in bus.list_names():
                if service.startswith("org.mpris.MediaPlayer2."):
                    player = bus.get_object(service, "/org/mpris/MediaPlayer2")

                    status = player.Get(
                        "org.mpris.MediaPlayer2.Player",
                        "PlaybackStatus",
                        dbus_interface="org.freedesktop.DBus.Properties",
                    )

                    metadata = player.Get(
                        "org.mpris.MediaPlayer2.Player",
                        "Metadata",
                        dbus_interface="org.freedesktop.DBus.Properties",
                    )
                    metadata = self._dbus_to_python(metadata)

                    if not metadata or "mpris:trackid" not in metadata:
                        continue

                    trackid = str(metadata["mpris:trackid"])

                    if (player_command.lower() in trackid.lower()) or (
                        "/org/mpd/" in trackid
                    ):
                        if "xesam:url" in metadata:
                            file_url = metadata["xesam:url"]
                            file_path = re.sub(r"file:\/\/", "", file_url)
                            file_path = unquote(file_path)

                            path = Path(file_path)
                            if path.exists() and path.is_file():
                                return path

            return None
        except Exception:
            return None
