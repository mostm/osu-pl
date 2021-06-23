import os
import shutil
import configparser

beatmap_dir = os.path.abspath(os.environ['LOCALAPPDATA']+'\\osu!\\Songs\\')
beatmaps = []
bm_osu = []

with os.scandir(os.path.abspath(beatmap_dir)) as it:
    for entry in it:
        if entry.is_dir():
            try:
                beatmap_id = int(str(entry.name).split(' ')[0])
            except ValueError:
                # I'm not sure what to do about unranked maps right now, we will exclude them
                continue
            beatmaps.append(entry.path)

beatmap_type = {
    "id": 0, # You may parse for "[Metadata]\n\nBeatmapSetID:{sid}" (WARN: Earlier maps will lack this parameter (osu file format v3 < osu file format v14)) or use the one provided with path
    "name": 'Author - Title', # I should get it from osu files rather than directory, but that's how it happens
    "audio": ".\\somefile.mp3", # Parse for "[General]\n\nAudioFilename: {filename}" | DONE
    "video": ".\\something.mp4" # Parse for "[Events]\n\nVideo,{timestamp},{filename}" (found mp4,avi,mpg) | plz check, TODO
}

for beatmap in beatmaps:
    with os.scandir(os.path.abspath(beatmap)) as it:
        bm = {
            'id': int(str(os.path.split(beatmap)[1]).split(' ')[0]),
            'name': str(os.path.split(beatmap)[1])[len(str(os.path.split(beatmap)[1]).split(' ')[0])+1:],
            'audio': None,
            'audio_length': None,
            'video': None
        }
        print('{} {}'.format(bm['id'], bm['name']))
        for entry in it:
            if entry.is_file():
                if entry.path.endswith('osu'):
                    # ConfigParser is actually overkill solution, although I set it up to work
                    # FixMe: This solution does not account for multiple (via diff) maps in one
                    #        Although, ranked maps should never have this.
                    with open(entry.path, 'r', encoding="utf-8") as f:
                        config_string = '[global]\n' + f.read()
                    a = ''
                    for x in config_string.split('\n')[:config_string.split('\n').index('[Events]')-1]:
                        a += x+'\n'
                    config = configparser.ConfigParser(allow_no_value=True)
                    config.read_string(a)
                    # TODO: Rewrite to simple checks and add video checking.
                    bm['audio'] = os.path.abspath(os.path.dirname(entry.path)+'\\'+config.get('General', 'AudioFilename'))
                elif entry.path.endswith('mp4') or entry.path.endswith('avi') or entry.path.endswith('mpg'):
                    bm['video'] = entry.path
        bm_osu.append(bm)


text_playlist = ""
for bm in bm_osu:
    if bm['audio']:
        text_playlist += "#EXTINF:0,{0}\n{1}\n".format(bm['name'], bm['audio'])

text_playlist = text_playlist[:-1]

try:
    with open('osu.m3u', 'w', encoding='utf-8') as file:
        file.write(text_playlist)
except:
    open('osu.m3u', 'x')
    with open('osu.m3u', 'w', encoding='utf-8') as file:
        file.write(text_playlist)

text_type = ""
for bm in bm_osu:
    if bm['name']:
        text_type += "{0}\n".format(bm['name'])
text_type = text_type[:-1]
try:
    with open('osu.txt', 'w', encoding='utf-8') as file:
        file.write(text_type)
except:
    open('osu.txt', 'x')
    with open('osu.txt', 'w', encoding='utf-8') as file:
        file.write(text_type)

for bm in bm_osu:
    if bm['audio']:
        print('{} {}'.format(bm['id'], bm['name']))
        if os.path.basename(bm['audio']).split('.')[-1] != '':
            shutil.copy2(bm['audio'], "{}\\osu music\\{}.{}".format(os.getcwd(), bm['name'], os.path.basename(bm['audio']).split('.')[-1]))
    if bm['video']:
        shutil.copy2(bm['video'], "{}\\osu music\\{}.{}".format(os.getcwd(), bm['name'], os.path.basename(bm['video']).split('.')[-1]))



print('done, ty for use')