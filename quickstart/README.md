# Simple Tutorial

This tutorial is walking through https://falcon.readthedocs.io/en/stable/user/quickstart.html#learning-by-example

## Setup

```shell
$ mamba create -p ./env -c conda-forge -y python=3.9
$ conda activate ./env
(env) $ python -m pip install uvicorn[standard] falcon cython
(env) $ uvicorn server:app
```

Once the server process fires up, use another shell to
```
curl localhost:8000/things
```
