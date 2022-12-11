from make import Context
from pty import spawn
from shlex import split
import docker

context = Context()


@context.target
def build_image():
    docker_client = docker.from_env()
    image, logs = docker_client.images.build(path=".")
    for log in logs:
        print(log)
    return image.id


@context.outdate
def outdate_image():
    return True


@context.target
def build_container(image):
    docker_client = docker.from_env()
    container = docker_client.containers.create(image)
    return container.id


@context.target
def build_shell(container):
    docker_client = docker.from_env()
    container_obj = docker_client.containers.get(container)
    container_obj.start()
    spawn(split(f'docker exec -it {container} /bin/bash'))


context.build()
