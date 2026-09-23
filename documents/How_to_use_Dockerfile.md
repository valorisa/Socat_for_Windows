# Procedure

## 1. Save the Dockerfile

In your app directory (where `requirements.txt` and the `socat/example.py` module are located):

```bash
ls
# you should see: Dockerfile  requirements.txt  socat/  ...
```

Make sure the contents of the `Dockerfile` match the generated version.

## 2. Build the image

From this directory:

```bash
docker build -t socat-api:1.8.1.0 .
```

- The `wget + ./configure + make + make install` step for socat will take some time on the first build.
- If the build fails, copy and share the end of the build logs.

## 3. Run the container

```bash
docker run --rm -p 8181:8181 --name socat-api socat-api:1.8.1.0
```

- The container should print gunicorn logs, with workers listening on `0.0.0.0:8181`.
 See also: [1](https://github.com/benoitc/gunicorn/issues/2138), [2](https://stackoverflow.com/questions/58429866/running-gunicorn-as-non-root-user)

## 4. Test from the host

In another terminal:

```bash
curl http://127.0.0.1:8181/
```

You should receive the response from `socat.example:app`.  
If you want, you can share the contents of `requirements.txt` and `socat/example.py` to double‑check that the `socat.example:app` target is correct.

[1] <https://github.com/benoitc/gunicorn/issues/2138>
[2] <https://stackoverflow.com/questions/58429866/running-gunicorn-as-non-root-user>
