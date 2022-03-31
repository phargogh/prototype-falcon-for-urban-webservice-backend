# More complex tutorial

## Setup

```shell
$ mamba create -p ./env -c conda-forge -y python=3.9
$ conda activate ./env
(env) $ pip install falcon httpx uvicorn
(env) $ uvicorn server:app
```
