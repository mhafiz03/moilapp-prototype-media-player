import os, subprocess
import numpy as np


cur_dir = os.path.dirname(__file__)
ffmpeg_exe = os.path.join(cur_dir, 'ffmpeg')

ffmpeg_cmd = [
    ffmpeg_exe,'-i'
]

maps = [
    '-i', f'{cur_dir}/xmap_1.pgm', '-i', f'{cur_dir}/ymap_1.pgm',
    '-i', f'{cur_dir}/xmap_2.pgm', '-i', f'{cur_dir}/ymap_2.pgm',
    '-i', f'{cur_dir}/xmap_3.pgm', '-i', f'{cur_dir}/ymap_3.pgm',
    '-i', f'{cur_dir}/xmap_4.pgm', '-i', f'{cur_dir}/ymap_4.pgm',
    '-i', f'{cur_dir}/xmap_5.pgm', '-i', f'{cur_dir}/ymap_5.pgm',
    '-i', f'{cur_dir}/xmap_6.pgm', '-i', f'{cur_dir}/ymap_6.pgm',
]


scale_down = 4
filters = [
    '-filter_complex',
       f'[0:v]split=6[v1][v2][v3][v4][v5][v6];\
       [v1][1][2]remap[v1r]; \
       [v2][3][4]remap[v2r]; \
       [v3][5][6]remap[v3r]; \
       [v4][7][8]remap[v4r]; \
       [v5][9][10]remap[v5r]; \
       [v6][11][12]remap[v6r]; \
       [v1r]scale=iw/{scale_down}:ih/{scale_down}[v1s]; \
       [v2r]scale=iw/{scale_down}:ih/{scale_down}[v2s]; \
       [v3r]scale=iw/{scale_down}:ih/{scale_down}[v3s]; \
       [v4r]scale=iw/{scale_down}:ih/{scale_down}[v4s]; \
       [v5r]scale=iw/{scale_down}:ih/{scale_down}[v5s]; \
       [v6r]scale=iw/{scale_down}:ih/{scale_down}[v6s]; \
       [v1s][v2s][v3s]hstack=inputs=3[row1]; \
       [v4s][v5s][v6s]hstack=inputs=3[row2]; \
       [row1][row2]vstack=inputs=2[out]'
]

output = ['-map', '[out]', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1']

width = 1944
height = 972
frame_size = width * height * 3


class CustomVideoCapture:
    def __init__(self, video_path, fps=10):
        ffmpeg_cmd.append(video_path)
        ffmpeg_cmd.append('-r')
        ffmpeg_cmd.append(str(fps))
        self.process = subprocess.Popen(ffmpeg_cmd + maps + filters + output, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self):
        raw_frame = self.process.stdout.read(frame_size)
        if len(raw_frame) < frame_size:
            return False, None
        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        return True, frame

    def release(self):
        self.process.stdout.close()
        self.process.wait()  

