# odoo-addons-parser

[![Version](https://img.shields.io/pypi/v/odoo-addons-parser.svg?maxAge=86400)](https://pypi.org/project/odoo-addons-parser)
[![Supported Versions](https://img.shields.io/pypi/pyversions/odoo-addons-parser.svg)](https://pypi.org/project/odoo-addons-parser)
[![Pre-commit Status](https://github.com/sebalix/odoo-addons-parser/actions/workflows/pre-commit.yml/badge.svg?branch=main)](https://github.com/sebalix/odoo-addons-parser/actions/workflows/pre-commit.yml?query=branch%3Amain)
[![Tests Status](https://github.com/sebalix/odoo-addons-parser/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/sebalix/odoo-addons-parser/actions/workflows/test.yml?query=branch%3Amain)

Python package to collect and analyze data from Odoo module folders without requiring an Odoo runtime. It performs static file analysis to extract useful information from Odoo modules.

## Features

- **Static Analysis**: Doesn't rely on any Odoo runtime; performs static files analysis
- **Code Statistics**: Count lines of code (Python, XML, JavaScript, and CSS)
- **Manifest Parsing**: Extract useful data from manifest files (authors, dependencies, etc.)
- **Model Extraction**: Extract Odoo models information (with fields and methods)
- **Data Extraction**: Extract data from XML and CSV files
- **Flexible Scanning**: Scan individual modules, repositories, or entire Odoo source code

## Installation

```bash
uv pip install odoo-addons-parser
```

Or with pip:
```bash
pip install odoo-addons-parser
```

## Usage

### ModuleParser

Parse a single Odoo module:

```python
from odoo_addons_parser import ModuleParser
from pprint import pprint as pp

mod = ModuleParser("/path/to/OCA/server-tools/server_environment")
pp(mod.to_dict())
```

Example output:

```python
{
    'code': {'CSS': 0, 'JavaScript': 0, 'Python': 541, 'XML': 21},
    'manifest': {
        'author': 'Camptocamp,Odoo Community Association (OCA)',
        'category': 'Tools',
        'data': ['security/ir.model.access.csv', 'security/res_groups.xml', 'serv_config.xml'],
        'depends': ['base', 'base_sparse_field'],
        'installable': True,
        'license': 'GPL-3 or any later version',
        'name': 'server configuration environment files',
        'summary': 'move some configurations out of the database',
        'version': '14.0.1.0.0',
        'website': 'https://github.com/OCA/server-env'
    },
    'models': ...,
    'name': 'server_environment'
}
```

### RepositoryParser

Parse a whole repository of addons:

```python
from odoo_addons_parser import RepositoryParser

repo = RepositoryParser("/path/to/OCA/server-tools")
pp(repo.to_dict())
```

### OdooParser

Parse the Odoo source code repository:

```python
from odoo_addons_parser import OdooParser

odoo = OdooParser("/path/to/odoo/odoo")
data = odoo.to_dict()
list(data["__odoo__"]["models"])
# ["BaseModel", "Model", "TransientModel"]
"res.partner" in data["base"]["models"]
# True
```

## Parameters

You can disable specific features using parameters:

```python
# Disable code statistics
repo = RepositoryParser("path/to/addons_path", code_stats=False)

# Disable model scanning
mod = ModuleParser("path/to/addons_path/module", scan_models=False)

# Disable data scanning
mod = ModuleParser("path/to/addons_path/module", scan_data=False)

# Disable all
odoo = OdooParser("/path/to/odoo/odoo", code_stats=False, scan_models=False, scan_data=False)
```

## License

This project is licensed under the LGPL-3.0 License - see the [LICENSE](LICENSE) file for details.
