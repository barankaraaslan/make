from __future__ import annotations
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Callable, TypeVar, ParamSpec, Any
from functools import wraps
from inspect import signature
from pathlib import Path
import logging
import json

T = TypeVar('T')
P = ParamSpec('P')


@dataclass
class Target:
    build_recipe: Callable
    value: Any
    dependency_build_info: dict[str, Any]
    outdate_recipe: Callable[[], bool] | None = None

    def is_outdated(self) -> bool:
        if self.outdate_recipe:
            return self.outdate_recipe()
        else:
            return self.value == None


def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"running {func.__name__} with {args}")
        print(f'result is {func(*args, **kwargs)}')
    return wrapper


def rget(_dict, *args):
    try:
        value = _dict
        for key in args:
            value = value[key]
        return value
    except KeyError:
        return None


STATE_FILENAME = 'state.json'


def read_state() -> dict[str, Any]:
    state_path = Path(STATE_FILENAME)
    if state_path.is_file():
        with open(state_path, "r") as state_file:
            state = json.loads(state_file.read())
            return state
    else:
        return {}


def write_state(registered_targets: dict[str, Target]):
    # generate a dictionary from registered_targets and write it as json
    state = {}
    for target_name, target in registered_targets.items():
        state[target_name] = {'value': target.value,
                              'dependency_build_info': target.dependency_build_info}
    with open(STATE_FILENAME, 'w') as state_file:
        json.dump(state, state_file)


class Context:
    def __init__(self) -> None:
        self.registered_targets: dict[str, Target] = dict()
        parser = ArgumentParser()
        parser.add_argument(
            '--log_level', choices=[logging.DEBUG, logging.INFO], default=logging.INFO)
        args = parser.parse_known_args()
        logging.basicConfig(level=logging.DEBUG)

    def target(self, build_recipe: Callable[P, T]) -> Callable[P, T]:
        target_name = build_recipe.__name__.removeprefix("build_")
        dependency_names = signature(build_recipe).parameters

        @wraps(build_recipe)
        def build_recipe_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logging.info(f"building {target_name}")
            target = self.registered_targets[target_name]
            result =  build_recipe(*args, **kwargs)
            target.dependency_build_info = dict(
                zip(dependency_names, args))
            target.value = result
            logging.info(
                f"finished building {target_name} with result: {target.value}")

        # read state and get saved value of target while creating Target object
        state = read_state()
        dependency_build_info = dict([(dependency_name, rget(state, target_name, 'dependency_build_info', dependency_name))
                                     for dependency_name in dependency_names])
        self.target_to_register = Target(
            build_recipe_wrapper, rget(
                state, target_name, 'value'), dependency_build_info)
        self.registered_targets[target_name] = self.target_to_register
        logging.debug(f"Registered {self.target_to_register}")
        return build_recipe_wrapper

    def outdate(self, outdate_recipe: Callable[P, bool]) -> Callable[P, bool]:
        target_name = outdate_recipe.__name__.removeprefix("outdate_")

        @wraps(outdate_recipe)
        def outdate_recipe_wrapper(*args: P.args, **kwargs: P.kwargs) -> bool:
            logging.info(f"checking {target_name}")
            target = self.registered_targets[target_name]
            result = outdate_recipe(*args, **kwargs)
            logging.info(
                f"finished checking {target_name} with result: {result}")
            return result


        self.registered_targets[target_name].outdate_recipe = outdate_recipe_wrapper
        logging.debug(f"registered outdate {outdate_recipe_wrapper} for {target_name}")
        return outdate_recipe_wrapper

    def build_target(self, target: Target) -> None:
        dependencies = [self.registered_targets[dependency_name]
                        for dependency_name in signature(target.build_recipe).parameters]
        for dependency in dependencies:
            if dependency.is_outdated():
                self.build_target(dependency)

        if target.is_outdated() or self.dependency_mismatch(target):
            dependency_values = [
                dependency.value for dependency in dependencies]
            target.build_recipe(*dependency_values)

    def dependency_mismatch(self, target: Target):
        return any(map(lambda dependency_name: self.registered_targets[dependency_name].value != target.dependency_build_info[dependency_name], signature(target.build_recipe).parameters))

    def build(self) -> None:
        parser = ArgumentParser()
        parser.add_argument('target_name')
        args = parser.parse_args()
        self.build_target(self.registered_targets[args.target_name])
        write_state(self.registered_targets)


if __name__ == "__main__":
    context = Context()
    logging.basicConfig(level=logging.DEBUG)

    @ context.target
    def build_image():
        return "hello worlda!"

    @ context.target
    def build_container(image):
        return "container_id"

    context.build()
