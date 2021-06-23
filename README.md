osu!pl
======
Export your osu! beatmaps as Music & Video Libraries and playlists

Requirements
------------
1. Install [ffmpeg](https://www.ffmpeg.org/) to PATH
2. For building, you gonna need pipenv: `pip install pipenv`

Install (Windows)
-----------------
Visit [releases](https://github.com/mostm/osu-pl/releases/latest), and grab latest one.

Build
-----
1. `git clone https://github.com/mostm/osu-pl.git`
2. `pipenv sync`
3. `pyinstaller main.spec`

Note: While project has been written to support multiplatform, osu!stable does not officially support multiplatform.

So there is no reason for me to test this under other platforms.
Submit your pull requests, if this becomes an issue for you.
