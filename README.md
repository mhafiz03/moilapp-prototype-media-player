# MoilApp Plugin To Play Video From One Fisheye Video Into 6 Views

https://github.com/mhafiz03/moilapp-prototype-media-player/assets/153695217/9dd46eb6-1f8a-4c13-abab-85957b9558ec

# Description
Inspired by `MAP_CACHE_ENABLED` in [cjchng/mainmoil_6view](https://github.com/cjchng/mainmoil_6view) and [FFMPEG](https://trac.ffmpeg.org/wiki/Creating%20multiple%20outputs)'s performance.

This is a showcase of using FFMPEG's `remap filter` instead of OpenCV's `remap` function.

# To make a PGM file:
```python
from PIL import Image
# no cv.imwrite() doesn't work because it only saves to 8-bit, while we need 16-bit.

map_x, map_y = moildev.maps_anypoint_mode1(alpha, beta, zoom)

Image.fromarray(map_x.astype(np.int16)).save("map_x.pgm")
Image.fromarray(map_y.astype(np.int16)).save("map_y.pgm")
```

# Generate Multiple Views Grid With A Single Map

This is wayyy **faster** than below and can go up to `60 fps` _(or stable at `30 fps`, on an `8 core` machine)_ so it can be used for **real time** video remap with **any arbitary number of maps**. _See [gen_maps_grid.py](gen_maps_grid.py)_

_(It takes around 30 seconds to generate 360 map pairs on same machine mentioned before, but with real time encoding speed)_.

## Examples For Grid On Single Map 
### 4x8 Grid
![](assets/example_4x8_views.jpg)

### 8x8 Grid
![](assets/example_8x8_views.jpg)

### 15x24 Grid (all 360 degrees on beta)
![](assets/example_15x24_views.jpg)

# FFMPEG Examples
Here are examples on using FFMPEG's remap filter _(and stack, scale, map, split filters but I they're not needed anymore since the above)_, also looking for a description? Please refer to [FFMPEG documentation](https://trac.ffmpeg.org/wiki/RemapFilter):

## For image
```sh
ffmpeg -i fisheye_image.jpg -i map_x.pgm -i map_y.pgm -lavfi remap output.png
```

## For video
```sh
ffmpeg -i fisheye_image.mp4 -i map_x.pgm -i map_y.pgm -lavfi remap output.mp4
```

## For 6 views
![](assets/example_6_views.jpg)
```sh
ffmpeg -i input_video.mp4 \
       -i xmap_1.pgm -i ymap_1.pgm \
       -i xmap_2.pgm -i ymap_2.pgm \
       -i xmap_3.pgm -i ymap_3.pgm \
       -i xmap_4.pgm -i ymap_4.pgm \
       -i xmap_5.pgm -i ymap_5.pgm \
       -i xmap_6.pgm -i ymap_6.pgm \
-filter_complex "\
       [0:v]split=6[v1][v2][v3][v4][v5][v6];\
       [v1][1][2]remap[v1r]; \
       [v2][3][4]remap[v2r]; \
       [v3][5][6]remap[v3r]; \
       [v4][7][8]remap[v4r]; \
       [v5][9][10]remap[v5r]; \
       [v6][11][12]remap[v6r]; \
       [v1r]scale=iw/4:ih/4[v1s]; \
       [v2r]scale=iw/4:ih/4[v2s]; \
       [v3r]scale=iw/4:ih/4[v3s]; \
       [v4r]scale=iw/4:ih/4[v4s]; \
       [v5r]scale=iw/4:ih/4[v5s]; \
       [v6r]scale=iw/4:ih/4[v6s]; \
       [v1s][v2s][v3s]hstack=inputs=3[row1]; \
       [v4s][v5s][v6s]hstack=inputs=3[row2]; \
       [row1][row2]vstack=inputs=2[out]" \
       -map "[out]" output_video.mp4
```

## For 8 anypoints, 1 panorama, and 1 original view
_(One view is not correct because accidentally put only x map as both maps for that one view, i.e instead of xmap and ymap, I did xmap and xmap)_
![](assets/example_8_more_views.jpg)
```sh
ffmpeg -i input_video.mp4 \
       -i xmap_1.pgm -i ymap_1.pgm \
       -i xmap_2.pgm -i ymap_2.pgm \
       -i xmap_3.pgm -i ymap_3.pgm \
       -i xmap_4.pgm -i ymap_4.pgm \
       -i xmap_5.pgm -i ymap_5.pgm \
       -i xmap_6.pgm -i ymap_6.pgm \
       -i xmap_7.pgm -i ymap_7.pgm \
       -i xmap_8.pgm -i ymap_8.pgm \
       -i xmap_pano.pgm -i ymap_pano.pgm \
-filter_complex "\
       [0:v]split=9[v0][v1][v2][v3][v4][v5][v6][v7][v8];\
       [v1][1][2]remap[v1r]; \
       [v2][3][4]remap[v2r]; \
       [v3][5][6]remap[v3r]; \
       [v4][7][8]remap[v4r]; \
       [v5][9][10]remap[v5r]; \
       [v6][11][12]remap[v6r]; \
       [v7][13][14]remap[v7r]; \
       [v8][15][16]remap[v8r]; \
       [v0][17][18]remap[pano_remap]; \
       [v1r]scale=iw/4:ih/4[v1s]; \
       [v2r]scale=iw/4:ih/4[v2s]; \
       [v3r]scale=iw/4:ih/4[v3s]; \
       [v4r]scale=iw/4:ih/4[v4s]; \
       [v5r]scale=iw/4:ih/4[v5s]; \
       [v6r]scale=iw/4:ih/4[v6s]; \
       [v7r]scale=iw/4:ih/4[v7s]; \
       [v8r]scale=iw/4:ih/4[v8s]; \
       [pano_remap]crop=iw:ih/4:0:ih/4[pano_c]; \
       [0:v]scale=iw/2:ih/2[orig]; \
       [v1s][v2s][v3s][v4s]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[anygrid]; \
       [anygrid][orig]hstack=inputs=2[anygrid_orig]; \
       [v5s][v6s][v7s][v8s]hstack=inputs=4[anyrow]; \
       [pano_c][anyrow][anygrid_orig]vstack=inputs=3[out]" \
       -map "[out]" output_video.mp4 
```

## For live streaming
**Note:** `-g` is for GOP (Group Of Pictures), make it the same as FPS of source video
```sh
ffmpeg -i input_video.mp4 \
       -i xmap_1.pgm -i ymap_1.pgm \
       -i xmap_2.pgm -i ymap_2.pgm \
       -i xmap_3.pgm -i ymap_3.pgm \
       -i xmap_4.pgm -i ymap_4.pgm \
       -i xmap_5.pgm -i ymap_5.pgm \
       -i xmap_6.pgm -i ymap_6.pgm \
-filter_complex "\
       [0:v]split=6[v1][v2][v3][v4][v5][v6];\
       [v1][1][2]remap[v1r]; \
       [v2][3][4]remap[v2r]; \
       [v3][5][6]remap[v3r]; \
       [v4][7][8]remap[v4r]; \
       [v5][9][10]remap[v5r]; \
       [v6][11][12]remap[v6r]; \
       [v1r]scale=iw/4:ih/4[v1s]; \
       [v2r]scale=iw/4:ih/4[v2s]; \
       [v3r]scale=iw/4:ih/4[v3s]; \
       [v4r]scale=iw/4:ih/4[v4s]; \
       [v5r]scale=iw/4:ih/4[v5s]; \
       [v6r]scale=iw/4:ih/4[v6s]; \
       [v1s][v2s][v3s]hstack=inputs=3[row1]; \
       [v4s][v5s][v6s]hstack=inputs=3[row2]; \
       [row1][row2]vstack=inputs=2[out]" \
       -map "[out]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency \
       -hls_time 10 -f hls output_stream.m3u8
```

## For live streaming and outputting it to 6 different files
```sh
ffmpeg -i input_video.mp4 \
       -i xmap_1.pgm -i ymap_1.pgm \
       -i xmap_2.pgm -i ymap_2.pgm \
       -i xmap_3.pgm -i ymap_3.pgm \
       -i xmap_4.pgm -i ymap_4.pgm \
       -i xmap_5.pgm -i ymap_5.pgm \
       -i xmap_6.pgm -i ymap_6.pgm \
-filter_complex "\
       [0:v]split=6[v1][v2][v3][v4][v5][v6];\
       [v1][1][2]remap[v1r]; \
       [v2][3][4]remap[v2r]; \
       [v3][5][6]remap[v3r]; \
       [v4][7][8]remap[v4r]; \
       [v5][9][10]remap[v5r]; \
       [v6][11][12]remap[v6r]; \
       [v1r]scale=iw/4:ih/4[v1s]; \
       [v2r]scale=iw/4:ih/4[v2s]; \
       [v3r]scale=iw/4:ih/4[v3s]; \
       [v4r]scale=iw/4:ih/4[v4s]; \
       [v5r]scale=iw/4:ih/4[v5s]; \
       [v6r]scale=iw/4:ih/4[v6s]" \
       -map "[v1s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view1_stream.m3u8 \
       -map "[v2s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view2_stream.m3u8 \
       -map "[v3s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view3_stream.m3u8 \
       -map "[v4s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view4_stream.m3u8 \
       -map "[v5s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view5_stream.m3u8 \
       -map "[v6s]" -y -c:v libx264 -g 10 -preset ultrafast -tune zerolatency -hls_time 10 -f hls view6_stream.m3u8
```
