#!/usr/bin/env python3

import csv
from dataclasses import dataclass
from functools import total_ordering
import logging
import pathlib
import json
import random

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

CONFIG_PATH = pathlib.Path("config")


@dataclass
class Planet:
    name: str
    resources: float
    influence: float
    technology: str
    type_: str

    def __post_init__(self):
        if self.resources >= 2 * self.influence:
            # Influence will mostly not be considered
            self.influence = 0
        elif self.influence >= 2 * self.resources:
            # Resources will mostly not be considered
            self.resources = 0
        else:
            # Let's assume it's used half the time for each
            self.resources = self.resources / 2
            self.influence = self.influence / 2


@dataclass
@total_ordering
class Tile:
    id_: int
    color: str
    planets: list[Planet]
    anomalies: list[str] = None

    def __post_init__(self):
        self.resources = self.influence = 0
        self.technology = self.type_ = ""
        self.wormholes = ""

        for planet in self.planets:
            self.resources += planet['resources']
            self.influence += planet['influence']
            self.technology += planet['technology']

        if self.anomalies:
            for anomaly in self.anomalies:
                if anomaly.startswith('Wormhole'):
                    self.wormholes += anomaly[-1]

        self.absolute_value = 0
        self.absolute_value += self.resources
        self.absolute_value += self.influence
        self.absolute_value += 2 * len(self.technology)
        if self.wormholes:
            if len(self.wormholes) - len(set(self.wormholes)) == 0:
                # We have no wormhole duplicate
                self.absolute_value += 1

    def __eq__(self, tile):
        return self.absolute_value == tile.absolute_value

    def __lt__(self, tile):
        return self.absolute_value < tile.absolute_value


@total_ordering
class Slice:
    def __init__(self, tiles: list[Tile]):
        self.tiles = tiles
        self.update_values()

    def update_values(self):
        self.resources = self.influence = self.absolute_value = 0
        self.technology = self.wormholes = ""

        for tile in self.tiles:
            self.resources += tile.resources
            self.influence += tile.influence
            self.technology += tile.technology
            self.wormholes += tile.wormholes
            self.absolute_value += tile.absolute_value

    def __eq__(self, slice_):
        return self.absolute_value == slice_.absolute_value

    def __lt__(self, slice_):
        return self.absolute_value < slice_.absolute_value

    def is_slice_unbalanced(self):
        if self.resources >= 2 * self.influence:
            return True
        if self.influence >= 2 * self.resources:
            return True

        return False

    def remove_best_tile(self, color='blue'):
        self.tiles.sort(reverse=True)
        for idx, tile in enumerate(self.tiles):
            if tile.color == color:
                return self.tiles.pop(idx)

    def remove_worst_tile(self, color='blue'):
        self.tiles.sort()
        for idx, tile in enumerate(self.tiles):
            if tile.color == color:
                return self.tiles.pop(idx)

    def remove_excessive_tile(self):
        if self.resources > self.influence:
            comparator = 'resources'
        else:
            comparator = 'influence'

        self.tiles.sort(key=lambda x: getattr(x, comparator), reverse=True)
        return self.tiles.pop(0)

    def add(self, tile: Tile):
        self.tiles.append(tile)
        self.update_values()

    def filter_tiles(self, color=None):
        for tile in self.tiles:
            if color and tile.color != color:
                continue
            yield tile

    def place_tiles(self) -> list[Tile]:
        random.shuffle(self.tiles)
        result = [None] * 7
        non_allocated = [1, 3, 5, 6]
        random.shuffle(non_allocated)

        def adjacent(pos_a, pos_b):
            return (
                pos_a == 0
                or pos_b == 0
                or (pos_a + 1) % 6 == pos_b
                or (pos_b + 1) % 6 == pos_a
            )

        multiple_anomalies = \
            len([tile for tile in self.tiles if tile.anomalies]) > 1
        # Place the blue tiles
        for i, tile in enumerate(self.filter_tiles(color='blue')):
            if i == 0 and multiple_anomalies:
                # If there are multiple anomalies, none can be placed on the
                # middle slot, thus we must force a blue tile to be there
                non_allocated.insert(0, 0)
            elif i == 0:
                # We don't care which tile goes to the middle slot
                non_allocated.insert(
                    random.randint(0, len(non_allocated) - 1),
                    0
                )
            result[non_allocated.pop(0)] = tile

        # Place the red tiles
        for tile in self.filter_tiles(color='red'):
            result[non_allocated.pop(0)] = tile

        self.tiles = result
        return result


def draw_all_tiles(tiles: list[Tile], players: int = 6):
    if players != 6:
        raise NotImplementedError("<6 players not handled yet")

    # Exclude a random blue tile
    random.shuffle(tiles)
    while True:
        tile = tiles.pop(0)
        if tile.color == 'red':
            tiles.append(tile)
        else:
            break

    return tiles


def generate_slices(tiles: list[Tile], k: int = 6) -> list[Slice]:
    if k != 6:
        raise NotImplementedError("<6 players not handled yet")

    slices = []

    # Pretty much random right now
    red_tiles = [t for t in tiles if t.color == 'red']
    random.shuffle(red_tiles)
    blue_tiles = [t for t in tiles if t.color == 'blue']
    random.shuffle(blue_tiles)

    for i in range(k):
        slice_tiles = []
        for j in range(2):
            slice_tiles.append(red_tiles.pop(0))
        for j in range(3):
            slice_tiles.append(blue_tiles.pop(0))

        slices.append(Slice(slice_tiles))

    return slices


def check_slice_balance(slices: list[Slice]) -> bool:

    # Check for slices much better than others
    if max(slices).absolute_value >= 1.5 * min(slices).absolute_value:
        return False

    # Check for unbalanced slices
    for slice_ in slices:
        if slice_.is_slice_unbalanced():
            return False

    return True


def rebalance_slices(slices):
    # Rebalance, if needed, between best and worst slices
    slices.sort()
    worst_slice, best_slice = slices[0], slices[-1]
    if best_slice.absolute_value >= 1.5 * worst_slice.absolute_value:
        LOG.warn("Rebalancing between best and worst slice")
        best_tile = best_slice.remove_best_tile()
        worst_tile = worst_slice.remove_worst_tile(color=best_tile.color)

        best_slice.add(worst_tile)
        worst_slice.add(best_tile)

    # Rebalance, if needed, between the slice with best and worst res/inf
    slices.sort(key=lambda x: x.resources / x.influence)
    most_influence_heavy_slice = slices[0]
    most_resources_heavy_slice = slices[-1]

    if (
        (
            most_influence_heavy_slice.influence
            >= 2 * most_influence_heavy_slice.resources
        )
        or
        (
            most_resources_heavy_slice.resources
            >= 2 * most_resources_heavy_slice.influence
        )
    ):
        LOG.warn("Rebalancing due to unbalanced res/inf ratio in slice")
        best_inf_tile = most_influence_heavy_slice.remove_excessive_tile()
        best_res_tile = most_resources_heavy_slice.remove_excessive_tile()

        most_resources_heavy_slice.add(best_inf_tile)
        most_influence_heavy_slice.add(best_res_tile)

    return slices


def prepare_slices():
    with open(CONFIG_PATH.joinpath("tiles.json")) as f:
        tiles_raw = json.load(f)

    with open(CONFIG_PATH.joinpath("planets.csv")) as f:
        planets = {r["name"]: r for r in csv.DictReader(f)}
        for p_name, p in planets.items():
            planets[p_name]['technology'] = p['technology'] or ''
            planets[p_name]['resources'] = int(p['resources'])
            planets[p_name]['influence'] = int(p['influence'])

    tiles = []
    for tile in tiles_raw:
        replaced_planets = []
        for planet_name in tile.get('planets', []):
            replaced_planets.append(planets[planet_name])
        tiles.append(Tile(
            tile['id'],
            tile['color'],
            replaced_planets,
            tile.get('anomalies')
        ))

    all_tiles = draw_all_tiles(tiles)

    slices = generate_slices(all_tiles)
    while True:
        success = check_slice_balance(slices)
        if success:
            break
        LOG.warn("Rebalacing slices")
        slices = rebalance_slices(slices)

    for slice_ in slices:
        slice_.place_tiles()

    return slices
