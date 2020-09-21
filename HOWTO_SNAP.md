Steps:

- First check that snapcraft can build something:

```
snapcraft
```

- Install it and try it, something like the following, replacing 
  the snap name with the one you just built:

```
sudo snap install --dangerous charmcraft_0.2.0+95.g6f8c4cc_amd64.snap
```

- If needs to be fixed, see section(s) below, GOTO 10


## How to add new Python dependencies

If trying a new snap fails because of import errors, you need to include new 
dependencies.The easiest way to do this is to open the snap, manually copy the 
needed dependency, and try it: if it keeps failing, keep adding more dependencies, 
else you're done and just update the `stage` section in `snapcraft.yaml` 
with what you brought in.

Let's go on that procedure. First, open the just built snap:

```
unsquashfs charmcraft_0.2.0+95.g6f8c4cc_amd64.snap 
```

Copy the dependencies files you need. For example, for the `tabulate` lib 
it needs to be included:

```
tabulate-0.8.7.dist-info
tabulate.py
```

Remember to not be *that* specific in `snapcraft.yaml`, where you could just 
annotate:

```
      - lib/tabulate-*.dist-info
      - lib/tabulate.py
```

You can find these files in the project's virtualenv. So:

```
cp env/lib/python3.8/site-packages/tabulate* squashfs-root/lib/
```

Install the snap from the unsquashed dir...

```
sudo snap try squashfs-root/
```

...and try again. 
