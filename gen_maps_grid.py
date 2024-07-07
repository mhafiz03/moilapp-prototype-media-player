import numpy as np
import cv2
from multiprocessing import Pool, cpu_count
from PIL import Image
from moildev import Moildev

moildev = Moildev("moildev/unitest/camera_parameters.json", "entaniya")
# moildev = Moildev("moildev/unitest/camera_parameters.json", "vivotek_fe8181")

zoom = 1.5
alpha = 45
grid_rows, grid_cols = 4, 8
total_maps = grid_rows * grid_cols
target_width = 1920

individual_target_width = target_width / grid_cols

beta_increment = 360 / total_maps
beta_values = [i * beta_increment for i in range(total_maps)]

def generate_map(beta_value):
    map_X, map_Y = moildev.maps_anypoint_mode1(alpha, beta_value, zoom)
    
    h, w = map_X.shape
    scaling_factor = individual_target_width / w
    new_w = int(w * scaling_factor)
    new_h = int(h * scaling_factor)
    
    x = cv2.resize(map_X.astype('int16'), (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    y = cv2.resize(map_Y.astype('int16'), (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    return x, y

if __name__ == '__main__':
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(generate_map, beta_values)

    maps_x, maps_y = zip(*results)

    h_stacks_x = []
    h_stacks_y = []

    for i in range(0, total_maps, grid_cols):
        h_stacks_x.append(np.hstack(maps_x[i:i + grid_cols]))
        h_stacks_y.append(np.hstack(maps_y[i:i + grid_cols]))

    grid_x = np.vstack(h_stacks_x)
    grid_y = np.vstack(h_stacks_y)

    Image.fromarray(grid_x).save("xmap_many_grid.pgm")
    Image.fromarray(grid_y).save("ymap_many_grid.pgm")
