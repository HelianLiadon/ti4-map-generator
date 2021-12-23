__version__ = '0.1.0'

from . import map_generation


def print_slices(slices):
    for idx, slice_ in enumerate(slices):
        print(f"Slice {idx+1}")
        print("=======")
        print("Tiles: {}".format(
            ", ".join([str(t.id_) for t in slice_.tiles if t])
        ))
        print(f"Absolute value : {slice_.absolute_value}")
        print(f"Total ressource: {slice_.resources}")
        print(f"Total influence: {slice_.influence}")
        print(f"Tech skips: {slice_.technology}")
        print(f"Wormholes: {slice_.wormholes}")


def generate_slices():
    slices = map_generation.prepare_slices()
    print_slices(slices)
