# Cheat sheet: build & push Docker image for socat 1.8.1.3

## Local directory

All commands below can be run from:

```text
C:\Users\<your_username>\Projets\socat-1.8.1.3\Install_from_dockerfile
```

This directory contains the `Dockerfile`, `requirements.txt` and the `socat/` package used by the image.

***

## 1. Build local image

```powershell
docker build -t socat-api:1.8.1.3 .
```

- `NAME` = `socat-api`  
- `TAG`  = `1.8.1.3`  

This creates a local image `socat-api:1.8.1.3` based on `python:3.14.2-slim-bookworm` with socat 1.8.1.3 compiled inside.

Check it:

```powershell
docker images socat-api
```

***

## 2. Tag image for Docker Hub

Docker Hub account:  

- `USER` = `your_Docker_ID`  
- `REPO` = `socat-1.8.1.3`  

Create tags for Docker Hub:

```powershell
docker tag socat-api:1.8.1.3 your_Docker_ID/socat-1.8.1.3:1.8.1.3
docker tag socat-api:1.8.1.3 your_Docker_ID/socat-1.8.1.3:latest
```

Here:

- Full remote name with explicit version:  
  `USER/REPO:TAG` = `your_Docker_ID/socat-1.8.1.3:1.8.1.3`  
- Full remote name with `latest`:  
  `your_Docker_ID/socat-1.8.1.3:latest` [[1](https://docs.docker.com/reference/cli/docker/image/push/), [2](https://docs.docker.com/get-started/docker-concepts/building-images/build-tag-and-publish-an-image/)]

***

## 3. Login to Docker Hub

```powershell
docker login
# username: your_Docker_ID
# password or access token
```

***

## 4. Push tags to Docker Hub

```powershell
docker push your_Docker_ID/socat-1.8.1.3:1.8.1.3
docker push your_Docker_ID/socat-1.8.1.3:latest
```

After this, the Docker Hub repository  
`https://hub.docker.com/r/your_Docker_ID/socat-1.8.1.3`  
shows the tags `1.8.1.3` and `latest` under the **Tags** tab. [[3](https://docs.docker.com/docker-hub/repos/manage/hub-images/tags/), [4](https://docs.docker.com/get-started/introduction/build-and-push-first-image/)]

***

## 5. Pull and run (from any machine)

```bash
docker pull your_Docker_ID/socat-1.8.1.3:1.8.1.3
docker run --rm -p 8181:8181 --name socat-api your_Docker_ID/socat-1.8.1.3:1.8.1.3
```

Then test:

```bash
curl http://127.0.0.1:8181/
# expected: "socat 1.8.1.3 Docker demo"
```
