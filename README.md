[![Pre-commit Status](https://github.com/sebalix/odoo-addons-parser/actions/workflows/pre-commit.yml/badge.svg?branch=main)](https://github.com/sebalix/odoo-addons-parser/actions/workflows/pre-commit.yml?query=branch%3Amain)
[![Tests Status](https://github.com/sebalix/odoo-addons-parser/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/sebalix/odoo-addons-parser/actions/workflows/test.yml?query=branch%3Amain)
[![Last version](https://img.shields.io/pypi/v/odoo-addons-parser)](https://pypi.org/project/odoo-addons-parser/)

# odoo-addons-parser

Python package to collect data from Odoo module folders.

Features:

- scan an Odoo repository, a folder of modules (repository) or a module only
- count the number of lines of code (Python, XML, JavaScript and CSS by default)
- read the manifest file (to get useful data like authors or dependencies)
- extract Odoo models info (fields, methods...)

## ModuleParser class

`ModuleParser` class aims to scan a module folder only:

```python
from odoo_addons_parser import ModuleParser
from pprint import pprint as pp

mod = ModuleParser("/path/to/OCA/server-tools/server_environment")
pp(mod.to_dict())
```
=>
```python
{'code': {'CSS': 0, 'JavaScript': 0, 'Python': 541, 'XML': 21},
 'manifest': {'author': 'Camptocamp,Odoo Community Association (OCA)',
              'category': 'Tools',
              'data': ['security/ir.model.access.csv',
                       'security/res_groups.xml',
                       'serv_config.xml'],
              'depends': ['base', 'base_sparse_field'],
              'installable': True,
              'license': 'GPL-3 or any later version',
              'name': 'server configuration environment files',
              'summary': 'move some configurations out of the database',
              'version': '14.0.1.0.0',
              'website': 'https://github.com/OCA/server-env'}},
 'models': ...
 'name': 'server_environment',
```

## RepositoryParser class

`RepositoryParser` class aims to scan a whole repository of addons
(also named *addons path*):

```python
from odoo_addons_parser import RepositoryParser
repo = RepositoryParser("/path/to/OCA/server-tools")
pp(repo.to_dict())
```
=>
```python
{'data_encryption': {'code': {'CSS': 0,
                              'JavaScript': 0,
                              'Python': 187,
                              'XML': 0},
                     'manifest': {'application': False,
                                  'author': 'Akretion, Odoo Community '
                                            'Association (OCA)',
                                  'category': 'Tools',
                                  'data': ['security/ir.model.access.csv'],
                                  'depends': ['base'],
                                  'development_status': 'Alpha',
                                  'external_dependencies': {'python': ['cryptography']},
                                  'installable': True,
                                  'license': 'AGPL-3',
                                  'name': 'Encryption data',
                                  'summary': 'Store accounts and credentials '
                                             'encrypted by environment',
                                  'version': '14.0.1.0.0',
                                  'website': 'https://github.com/OCA/server-env'},
                     'models': ...,
                     'name': 'data_encryption'},
 'mail_environment': {'code': {'CSS': 0,
                               'JavaScript': 0,
                               'Python': 43,
                               'XML': 0},
                      'manifest': {'author': 'Camptocamp, Odoo Community '
                                             'Association (OCA)',
                                   'category': 'Tools',
                                   'depends': ['fetchmail',
                                               'server_environment'],
                                   'license': 'AGPL-3',
                                   'name': 'Mail configuration with '
                                           'server_environment',
                                   'summary': 'Configure mail servers with '
                                              'server_environment_files',
                                   'version': '14.0.1.0.0',
                                   'website': 'https://github.com/OCA/server-env'},
                     'models': ...,
                     'name': 'mail_environment'},
[...]
```

## OdooParser class

`OdooParser` special class aims to scan the Odoo source code repository
(the one we clone from https://github.com/odoo/odoo). It'll parse the content
of `./odoo/addons`, `./addons` and Odoo base classes such as `BaseModel`,
`Model` and `TransientModel`:

```python
>>> from odoo_addons_parser import OdooParser
>>> odoo = OdooParser("/path/to/odoo/odoo")
>>> data = odoo.to_dict()
>>> list(data["__odoo__"]["models"])
["BaseModel", "Model", "TransientModel"]
>>> "res.partner" in data["base"]["models"]
True
```

## Parameters

Code stats or models scanning can be disabled thanks to `code_stats` and
`scan_models` parameters, available on all classes:

```python
repo = RepositoryParser("path/to/addons_path", code_stats=False)
mod = ModuleParser("path/to/addons_path/module", scan_models=False)
odoo = OdooParser("path/to/odoo/odoo", code_stats=False)
```
