#!/usr/bin/python3
'''
TODO:
- Check for FFMPEG before running
'''

import json
import os
import argparse
import subprocess
import concurrent.futures

def setupArgs():
    parser = argparse.ArgumentParser(
        prog = "episode-ripper",
        description = 'Take a ripped video file and split it at your time points',
        epilog = 'Big Ups to Liquid Richard'
    )

    parser.add_argument('-c', '--config', action='store', dest='config', default='{}/times.json'.format(os.getcwd()),
                        help='Pass the location of your yaml configuration here. Defaults to ${CWD}/config.yaml')
    
    return parser.parse_args()


# Times is a tuple of two times
def ffmpeg_split(times, filename, episode_num, new_files, concat=False):
    split_file = f"{episode_num}_{filename}"
    # If you want to concat the split files, need intermediate MPEG2-Transport Stream files
    if concat:
        prefix = filename.split('.')[0]
        split_file = f'_{episode_num}.ts'
    
    args = ["ffmpeg", "-ss", times[0], "-t", times[1], "-i", filename, "-c", "copy", split_file]

    new_files.append(split_file)
    return subprocess.Popen(args, stdin=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ffmpeg_concat(files, output_file, vcodec=None, acodec=None):
    vid_codec = vcodec if vcodec else "libx264"
    audio_codec = acodec if acodec else "copy"
    file_str = ''
    for f in files:
        file_str = f'{file_str}|{f}'
    # Remove incorrect leading pipe
    if file_str[0] == '|':
        file_str = file_str[1:]
    args = ["ffmpeg", "-i", f'concat:{file_str}', "-c:v", vid_codec, "-c:a", audio_codec, f'merged_{output_file}']
    #subprocess.Popen(args, stdin=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.Popen(args, stdin=None)

def main():
    argparser = setupArgs()

    config_json = argparser.config

    # Read json file
    try:
        with open(config_json, 'r') as jsonfile:
            try:
                json_data = json.load(jsonfile)
            except json.JSONDecodeError as je:
                print(f'{je.msg}::{je.lineno}')
                exit(1)
    except OSError:
        print(f'Config file {config_json} does not exist, exiting!')
        exit(1)
    
    file_objs = json_data.keys()
    for fo in file_objs:
        file_data = json_data[fo]
        times = file_data['times']
        concat = file_data['merge_clips']
        filename = file_data['filename']

        if not len(times) % 2 == 0:
            raise ValueError("Invalid number of split times given, should be even since you need a start and end")

        num_splits = int(len(times) / 2)
        splits = []

        # This needs to run for each file in the list
        for i in range(0,num_splits):
            start = f'start_{i+1}'
            end = f'end_{i+1}'
            splits.append((times[start],times[end]))

        new_files = []
        split_processes = []
        for idx,time in enumerate(splits):
            split_processes.append(ffmpeg_split(time, filename, idx+1, new_files, concat=concat))
        for p in split_processes:
            # Wait for all splits to finish so there's no race conditions
            p.communicate()
    
        if concat:
            concat_proc = ffmpeg_concat(new_files, filename)
            concat_proc.communicate()
            concat_proc.wait()
            for f in new_files:
                try:
                    os.remove(f)
                except:
                    print("Couldn't remove intermediate files.")
                    exit(1)

if __name__ == '__main__':
    main()