# Copyright 2022 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

"""Script to visualize metrics when running Charmcraft with --measure.

It needs the following dependencies, for which you can use fades:

    matplotlib
"""

import argparse
import itertools
import json
import time

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

Y_STEPS = 10
COLORS = itertools.cycle(mcolors.TABLEAU_COLORS)


def main(filepath):
    """Main entry point."""

    with open(filepath, "rt") as fh:
        results = json.load(fh)

    baseline = results.pop("__meta__")["baseline"]

    by_parent = {}
    for mid, info in results.items():
        by_parent.setdefault(info["parent"], []).append(mid)

    layers = []
    locating = [None]
    while locating:
        layer = []
        print("====== locating", locating)
        for parent in locating:
            for mid in by_parent.get(parent, []):
                layer.append(mid)

        print("====== layer", layer)
        if layer:
            layers.append(layer)
        locating = layer

    # get the measurement limits to only show texts when relevant
    max_t = max(measurement["tend"] for measurement in results.values())
    wide_metric = max_t * 0.05  # more than 5% of the total

    fig, ax = plt.subplots()

    layer_y_pos = (len(layers) - 1) * Y_STEPS
    layer_height = Y_STEPS * .99
    for layer in layers:
        measurements = [results[mid] for mid in layer]

        # the bars
        x_ranges = []
        for measurement in measurements:
            x_ranges.append((measurement["tstart"], measurement["tend"] - measurement["tstart"]))
        print("======== xr", x_ranges)
        colors = [next(COLORS) for _ in x_ranges]
        print("======== colors", colors)
        ax.broken_barh(x_ranges, (layer_y_pos, layer_height), facecolors=colors)

        # the texts
        text_y_pos = layer_y_pos + Y_STEPS / 2
        for measurement in measurements:
            if measurement["tend"] - measurement["tstart"] > wide_metric:
                rotation = 0
            else:
                rotation = 90
            text = measurement["msg"]
            if measurement["extra"]:
                text += "\n" + str(measurement["extra"])
            bar_center = (measurement["tend"] + measurement["tstart"]) / 2
            ax.text(
                x=bar_center, y=text_y_pos, s=text,
                ha='center', va='center', color='black', rotation=rotation)

        layer_y_pos -= Y_STEPS

    ax.set_yticklabels([])
    ax.set_xlabel("seconds")
    plt.title(f"Measurements took at {time.ctime(baseline)}")
    plt.xlim([0, max_t])
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filepath",
        help="The output of metrics after using --measure in Charmcraft")
    args = parser.parse_args()
    main(args.filepath)
