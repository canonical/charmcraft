import json
import time
import uuid

_baseline = time.time()


class _Measurements:
    def __init__(self):
        self.parents = [None]
        self.measurements = {}

    def start(self, msg, extra_info):
        this_id = uuid.uuid4().hex
        parent_id = self.parents[-1]
        self.parents.append(this_id)
        print(f"============= MT start {this_id} (parent {parent_id})")

        self.measurements[this_id] = {
            "parent": parent_id,
            "msg": msg,
            "extra": extra_info,
            "tstart": time.time()
        }
        return this_id

    def end(self, measurement_id):
        print("============= MT end!!", measurement_id)
        self.measurements[measurement_id]["tend"] = time.time()
        self.parents.pop()


_measurements = _Measurements()


class Timer:
    def __init__(self, msg, **extra_info):
        self.msg = msg
        self.extra_info = extra_info
        self.measurement_id = None

    def __enter__(self):
        self.measurement_id = _measurements.start(self.msg, self.extra_info)

    def __exit__(self, *exc):
        _measurements.end(self.measurement_id)


def timer_decorator(msg):
    def decorator(func):
        def _f(*args, **kwargs):
            with Timer(msg):
                return func(*args, **kwargs)
        return _f
    return decorator


def dump(filename):
    measurements = _measurements.measurements.copy()
    for m in measurements.values():
        m["tstart"] -= _baseline
        m["tend"] -= _baseline
    measurements["__meta__"] = {"baseline": _baseline}
    with open(filename, "wt") as fh:
        json.dump(measurements, fh, indent=4)


def merge_metrics_from(filename):
    with open(filename, "rt") as fh:
        to_merge = json.load(fh)

    # add the measurements from the file to this process ones, and while doing that
    # hook "root" measurements to current one and shift times
    current_id = _measurements.parents[-1]
    sublayer_baseline = to_merge.pop("__meta__")["baseline"]

    for mid, data in to_merge.items():
        data["tstart"] += sublayer_baseline
        data["tend"] += sublayer_baseline
        if data["parent"] is None:
            data["parent"] = current_id
        _measurements.measurements[mid] = data
