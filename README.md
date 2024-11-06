# pypedal

A Python-based command line tool.

## Installation

```bash
pip install -e .
```

## Usage

Show help:
```bash
pypedal --help
```

Process a file:
```bash
pypedal process input.txt -o output.txt
```

Show system information:
```bash
pypedal info
```

Enable debug mode:
```bash
pypedal info --debug
```

## Development

Run tests:
```bash
python -m pytest tests/
```

## Project Structure

```
pypedal/
├── pypedal/
│   ├── __init__.py
│   └── cli.py
├── tests/
│   └── test_cli.py
├── setup.py
└── README.md
