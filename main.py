import os
import shutil
from pathlib import Path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import ffmpeg
import mimetypes

EasyID3.RegisterTextKey('comment', 'COMM')


def parse_beatmap(content):
    section = None
    section_content = None
    pure_sections = ['events', 'timingpoints']
    beatmap = {}
    for line in content.split('\n'):
        if line.startswith('//'):
            continue
        if line.startswith('['):
            if section and section_content:
                beatmap[section] = section_content
            section = line[1:line.index(']')].lower()
            section_content = dict()
            if section in pure_sections:
                section_content = list()
            continue
        if section in pure_sections:
            section_content.append(line)
        elif section and ':' in line:
            key = line[:line.index(':')].lower()
            value = line[line.index(':') + 1:].strip()
            section_content[key] = value
    return beatmap


def scan_beatmaps(root):
    beatmap_sets = {}
    for beatmap_path in Path(root).glob('**/*.osu'):
        file = open(str(beatmap_path), 'r', encoding='utf-8').read()
        beatmap = parse_beatmap(file)
        beatmap_set = beatmap['metadata'].get('beatmapsetid')
        if not beatmap['metadata'].get('beatmapsetid'):
            p = beatmap_path.parent
            beatmap_set = p.name.split(' ')[0]
            if not beatmap_set.isdigit():
                beatmap_set = 'Unranked'
        bg = None
        video = None
        for event in beatmap['events']:
            if event.startswith('0,0,'):
                bg = event.split(',')[2].strip('"').strip()
            if event.startswith('Video'):
                video = [x.strip('"') for x in event.split(',')[1:]]
                video = {'timing': video[0], 'filename': video[1]}
        beatmap['background'] = bg
        beatmap['video'] = video
        beatmap['path'] = str(beatmap_path)
        if not beatmap_sets.get(beatmap_set):
            beatmap_sets[beatmap_set] = list()
        beatmap_sets[beatmap_set].append(beatmap)
    return beatmap_sets


def generalize_beatmap_sets(beatmap_sets):
    # Generalize to only relevant data
    generalized = {}
    unique_warn = []
    if beatmap_sets.get('Unranked'):
        beatmap_sets.pop('Unranked')
    for setid in beatmap_sets.keys():
        set_data = {}
        for map in beatmap_sets[setid]:
            data = map['metadata']
            data.pop('version')
            if data.get('beatmapid'):
                data.pop('beatmapid')
                data.pop('beatmapsetid')
            beatmap_dir = Path(map['path']).parent
            data['audio'] = None
            if map['general']['audiofilename']:
                data['audio'] = str(beatmap_dir.joinpath(map['general']['audiofilename']).absolute())
            data['video'] = map['video']
            if data['video']:
                data['video']['filename'] = str(beatmap_dir.joinpath(data['video']['filename']).absolute())
                if not os.path.exists(data['video']['filename']):
                    if setid not in unique_warn:
                        print(f'Video for {setid} is mentioned, but doesn\'t exist!')
                        unique_warn.append(setid)
                    data['video'] = None
            data['thumbnail'] = None
            if map['background']:
                data['thumbnail'] = str(beatmap_dir.joinpath(map['background']).absolute())
            for k, v in data.items():
                if not v:
                    continue
                if not set_data.get(k) or all([k == 'thumbnail', v != '', v]):
                    set_data[k] = v
                if set_data.get(k) != v:
                    if k == 'tags' and len(v) > len(set_data.get(k)):
                        set_data[k] = v
                    # print(f"{map['path']}: Conflict of data with set ({k}) | {set_data.get(k)} != {v}")
        generalized[setid] = set_data
    return generalized


def clean_and_allow_filename(dirty_filename, invalid='<>:"/\|?*'):
    fn = str(dirty_filename)
    for char in invalid:
        fn = fn.replace(char, '')
    return fn


def generate_library(beatmap_sets, music=True, video=False, music_target=None, video_target=None):
    if music:
        if not music_target:
            music_target = f'{os.getcwd()}{os.path.sep}osu!MusicLibrary'
        try:
            os.mkdir(f"{music_target}")
        except:
            pass
        for setid, beatmap in beatmap_sets.items():
            try:
                map = dict(beatmap)
                dir_name = f"{map['title']} by {map['artist']} ({map['creator']})"
                dir_name = clean_and_allow_filename(dir_name)
                try:
                    os.mkdir(f"{music_target}{os.path.sep}{dir_name}")
                except:
                    pass
                if not map['audio'] or map['audio'] == 'virtual':
                    continue
                ext = os.path.splitext(map['audio'])[1]
                fn = f"{map['artist']} - {map['title']}{ext}"
                fn = clean_and_allow_filename(fn)
                file_target = f"{music_target}{os.path.sep}{dir_name}{os.path.sep}{fn}"
                shutil.copy2(map['audio'], file_target)
                map['audio'] = file_target
                if map.get('thumbnail') and os.path.exists(map['thumbnail']):
                    ext = os.path.splitext(map['thumbnail'])[1]
                    file_target = f"{music_target}{os.path.sep}{dir_name}{os.path.sep}cover{ext}"
                    shutil.copy2(map['thumbnail'], file_target)
                    map['thumbnail'] = file_target
                audiofile = mutagen.File(map['audio'], easy=True)
                if audiofile:
                    audiofile['artist'] = map['artist']
                    audiofile['album'] = map['creator']
                    audiofile['albumartist'] = map.get('artistunicode') if map.get('artistunicode') else map['artist']
                    audiofile['title'] = map['title']
                    if map.get('tags'):
                        audiofile['comment'] = map['tags']
                    audiofile['tracknumber'] = ['1', '1']
                    audiofile.save()
                    if map.get('thumbnail') and not map['audio'].endswith('.ogg'):
                        audio = mutagen.File(map['audio'], easy=False)
                        if 'audio/vorbis' in audio.mime:
                            continue
                        with open(map.get('thumbnail'), 'rb') as albumart:
                            audio['APIC'] = APIC(
                                encoding=3,
                                mime=mimetypes.guess_type(map.get('thumbnail')),
                                type=3, desc='osu! Beatmap Thumbnail',
                                data=albumart.read()
                            )
                        audio.save()
            except Exception as error:
                print(f'[Music] Failure while processing {setid} | {type(error)} | {str(error)}')
    if video:
        if not video_target:
            video_target = f'{os.getcwd()}{os.path.sep}osu!VideoLibrary'
        try:
            os.mkdir(f"{video_target}")
        except:
            pass
        for setid, beatmap in beatmap_sets.items():
            try:
                if not beatmap.get('video') or beatmap.get('audio').endswith('virtual'):
                    continue
                map = dict(beatmap)
                fn = f"{map['artist']} - {map['title']} ({map['creator']}).mp4"
                output_fp = f"{video_target}{os.path.sep}{clean_and_allow_filename(fn)}"
                audio_in = ffmpeg.input(map['audio'])['a']
                kw = {}
                if map['video']['timing'] != '0':
                    kw['itsoffset'] = float(map['video']['timing']) / 1000
                video_in = ffmpeg.input(map['video']['filename'], **kw)
                streams = ffmpeg.probe(map['video']['filename'])['streams']
                ow = False
                for stream in streams:
                    if stream.get('codec_name') in ['h264', 'avc1', 'mpeg4']:
                        video_in = video_in[str(stream['index'])]
                        ow = True
                if not ow:
                    for stream in streams:
                        if stream.get('codec_name') not in ['h264', 'avc1', 'mpeg4']:
                            output_fp = output_fp[:-len('mp4')] + 'mkv'
                out = ffmpeg.output(audio_in, video_in, output_fp, vcodec='copy', acodec='copy', fflags='+genpts')
                print(' '.join(out.compile()))
                out.run(overwrite_output=True)
            except Exception as error:
                print(f'[Video] Failure while processing {setid} | {type(error)} | {str(error)}')
    return


if __name__ == '__main__':
    root = os.path.abspath(os.environ['LOCALAPPDATA'] + '\\osu!\\Songs\\')
    print('Scanning Beatmaps')
    beatmap_sets = scan_beatmaps(root)
    print('Generalizing beatmap data')
    beatmaps = generalize_beatmap_sets(beatmap_sets)
    print('Generating Music & Video Libraries')
    generate_library(beatmaps,
                     music=input('Music Library? (y/n) ').lower().startswith('y'),
                     video=input('Video Library? (y/n) ').lower().startswith('y'))
    print('Done, thanks for usage!')
