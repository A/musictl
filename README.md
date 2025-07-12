## Musictl

```
$ musictl       
Usage: musictl <command>
Commands:
  select        - Browse and play music
  pick <dir>    - Move current track to directory
  delete        - Delete current track
```

```
$ cat ~/.config/musictl/config.yml 
base_path: ~/Dropbox
ignored_dirs:
  - downloads
  - .git
  - __pycache__

music_directories:
  - collection
  - inbox
  - dj

music_extensions:
  - .mp3
  - .flac
  - .wav
  - .ogg
  - .m4a

player_command: deadbeef

track_count_options:
  - 10
  - 50
  - 100
  - ALL
 @A/musictl ❯ 
```

```
$ tree -L2 ~/Dropbox/
/home/anton/Dropbox/
├── collection
│   ├── ambient
│   ├── chillhop
│   ├── indie_rock
│   ├── instrumental_hip_hop
│   ├── jazz
│   ├── jazz_chill
│   ├── pop
│   ├── sovietwave
│   ├── synth_pop
│   └── synthwave
└── inbox
    ├── ambient_inbox
    ├── chillhop_inbox
    ├── jazz_downloads
    ├── jazz_inbox
    ├── leftfield_inbox
    ├── rock_inbox
    ├── soundtracks_inbox
    └── synthwave_inbox
```
