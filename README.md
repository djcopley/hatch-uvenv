# hatch-uvenv

This provides a plugin for [Hatch](https://github.com/pypa/hatch) that creates
[environments](https://hatch.pypa.io/latest/environment/) using UV's locked virtual environment
capabilities for fast, reproducible Python dependency management.

[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![Lint](https://github.com/djcopley/hatch-uvenv/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/djcopley/hatch-uvenv/actions/workflows/lint.yml)
[![PyPI version](https://badge.fury.io/py/hatch-uvenv.svg)](https://badge.fury.io/py/hatch-uvenv)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/hatch-uvenv.svg)](https://pypi.python.org/pypi/hatch-uvenv/)
[![Downloads](https://static.pepy.tech/badge/hatch-uvenv)](https://pepy.tech/project/hatch-uvenv)

**Table of Contents**

- [Installation](#installation)
- [Configuration](#configuration)
  - [Dependencies](#dependencies)

## Installation

- ***pyproject.toml***

    ```toml
    [tool.hatch.env]
    require = ["hatch-uvenv"]
    ```

- ***hatch.toml***

    ```toml
    [env]
    require = ["hatch-uvenv"]
    ```

## Configuration

The [environment plugin](https://hatch.pypa.io/latest/plugins/environment/) name is `uvenv`.

- ***pyproject.toml***

    ```toml
    [tool.hatch.envs.<env_name>]
    type = "uvenv"
    ```

- ***hatch.toml***

    ```toml
    [envs.<env_name>]
    type = "uvenv"
    ```

### Dependencies

UV's locked environments ensure that dependencies are installed in a fast and deterministic manner.
The environment will resolve dependencies based on a lockfile, ensuring reproducibility.

Example config:

```toml
[envs.<ENV_NAME>]
uv-flags = [
  "--all-packages",
]
groups = [
  "dependency-group-1",
  "dependency-group-2",
]
features = [
  "feature-1",
  "feature-2",
]
```
