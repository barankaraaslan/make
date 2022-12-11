# make

A make implementation that will provide functionality that i need.

Instead of tracking dependencies between only file targets, it can track arbitrary targets. Such as a docker image, a docker container

An example usage is shown in `example/`, import the `Context` and register your target's build commands.

If you want to customize decision process of a how a target is marked as outdated, you can provide custom functions to target

Future Steps:

- Provide some target types with same build and outdate functions, (Such as a `File` target that will check timestamp on the file to mark as outdated)

- Improve function registering process. Currently make will guess what target a function will build from the registered function name. Will provide decorator paramaters to explicitly define which target will that function will build

- Add parallel build with `graphlib` standart library
