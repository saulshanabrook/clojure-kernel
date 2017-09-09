# clojure-kernel

Clojure kernel for Jupyter that uses Leiningen.


## TODO

1. Move all to transports, use only one client per thingy
2. make to callback
3. also make transport for starting lein

## Install

You can either install with Conda, or manually.

### Conda (reccomended)

```bash
conda install -c conda-forge clojure-kernel
```

### Manually

Requirements:

* Leiningen
* Jupyter
* Python > 3.6

```bash
pip install clojure-kernel

```

## Development

```bash
pip install flit
flit install
```

## How it works

Jupyter starts each kernel in the base notebook directory. This means if we run `lein` in our kernel, it will use the `project.clj` defined in the directory you have open with Jupyter, if it exists.

1. Read [connection file](https://jupyter-client.readthedocs.io/en/latest/kernels.html#connection-files.)


## Prior Work

This project uses some concepts from Antoine Chesnais's [CLJ-Jupyter](https://github.com/achesnais/clj-jupyter) project.
