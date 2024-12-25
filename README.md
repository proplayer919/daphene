# Daphene

Daphene is a containerized script management tool designed for running isolated scripts using virtual environments. This README explains its usage and provides a detailed guide to its features and configuration.

## Features

- Initialize containers with metadata and scripts.
- Run scripts inside isolated environments.
- Support for Python and NodeJS virtual environments.
- Clean up temporary directories created during execution.
- Customizable container metadata with JSON configuration.
- CLI arguments for flexibility.

---

## Table of Contents

1. [Installation](#installation)
2. [Usage](#usage)
3. [CLI Arguments](#cli-arguments)
4. [Examples](#examples)
5. [Common Errors and Troubleshooting](#common-errors-and-troubleshooting)
6. [Contributing](#contributing)
7. [License](#license)

---

## Installation

### Prerequisites

- Python 3.8 or later.
- `colorama` package for colored output.
- `flask` package for static file serving.

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## Usage

Run Daphene using the following command (assuming you are currently in the Daphene's root directory):

```bash
python src/daphene.py [OPTIONS]
```

---

## CLI Arguments

### Primary Arguments

- `--run, -r` : Specify the container to run.
  - Example: `--run mycontainer`
- `--init, -i` : Initialize a new container.
- `--defaults, -d` : Use default values when initializing a container.
- `--list, -l` : List all available containers.

---

## Examples

### Initialize a Container

```bash
python daphene.py --init
```

Follow the prompts to provide container details. Use `--defaults` to skip the prompts and initialize with default values.

### Run a Container

```bash
python daphene.py --run mycontainer
```

### List Containers

```bash
python daphene.py --list
```

---

## Common Errors and Troubleshooting

### Error: Unsupported Platform

**Cause**: Attempting to run Daphene on an unsupported platform.

**Solution**: Ensure that your platform is either Windows or Linux. MacOS support may require additional configuration.

### Error: Failed to Create Virtual Environment

**Cause**: Missing or incorrectly installed runtimes.

**Solution**: Reinstall the runtimes from the GitHub repository.

### Error: No Such Script in Container

**Cause**: The specified script does not exist in the container metadata.

**Solution**: Verify the script name in the container's `.daphene/meta.json` file and ensure the file path is correct.

---

## Contributing

Contributions to Daphene are welcome! Follow these steps to get started:

1. Fork the repository and clone it to your local machine.
2. Create a new branch for your feature or bug fix:

   ```bash
   git checkout -b feature-or-bugfix-name
   ```

3. Make your changes and test thoroughly.
4. Commit your changes with a descriptive message:

   ```bash
   git commit -m "Description of the changes made"
   ```

5. Push your changes to your forked repository:

   ```bash
   git push origin feature-or-bugfix-name
   ```

6. Open a pull request and provide a detailed description of your changes.

### Guidelines

- Follow PEP 8 for Python code style.
- Include unit tests for new features or bug fixes.
- Keep commits focused and avoid unrelated changes.

---

## License

Daphene is licensed under the MIT License. See `LICENSE` for details.
