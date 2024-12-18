# README

## About this project

- Remoteperf is a performanc emeasurement library written in python. It's designed to work on remote systems, connecting via ssh or adb
and using basic tooling in order to extract performance data to then parse it. The ibrary is designed to work out-of-the-box on as wide
variety of systems as possible by using basic shell-scripting and standard command-line tools (_such as cat, grep, sed, ls etc_).

- Featres: measuring cpu and memory, system-wide or process-wise, in the background or single measurements, on linux, android, and QNX.

- Limitations: Currently, spawning background processes on a target which produces data

## Pre-requisites

- nox
- python 3.8+

## Testing

[Pytest](https://pytest.readthedocs.io/en/latest/) is used to run python unit test together with
[Nox](https://nox.readthedocs.io/en/latest/) to create a virtual environments.

Execute

```bash
nox -e test
```

To run multithreaded with 8 threads:

```bash
nox -e test -- -n 8
```

### Integration testing

To run integration tests, run

```bash
nox -e integration_test
```

To keep the container alive for debugging or avoiding startup and teardown each time, run

```bash
nox -e integration_test -- keep_container
```

Building remains a manual step for now:

```bash
nox -e build_integration_image
```

### Releasing

TODO

## Contributing

See the [contributing guide](CONTRIBUTING.md) for detailed instructions on how to get started with this project.

## Code of Conduct

This project adheres to the [Code of Conduct](./.github/CODE_OF_CONDUCT.md). By participating, you are expected to honor this code.

## License

This repository is licensed under [Apache License 2.0](LICENSE) © [2024] Volvo Car Corporation.
