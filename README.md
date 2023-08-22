odoo-addons-analyzer
====================

Python package to collect data from Odoo module folders.

Features:

- scan a folder of modules (repository) or a module only
- count the number of lines of code (Python, XML, JavaScript and CSS by default)
- read the manifest file (to get useful data like authors or dependencies)

Example with `ModuleAnalysis` class:

```python
from odoo_addons_analyzer import ModuleAnalysis
from pprint import pprint as pp

ma = ModuleAnalysis("/path/to/OCA/server-tools/server_environment")
pp(ma.to_dict())
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
              'website': 'https://github.com/OCA/server-env'}}
```

With `RepositoryAnalysis` class:

```python
from odoo_addons_analyzer import RepositoryAnalysis
ra = RepositoryAnalysis("/path/to/OCA/server-tools")
pp(ra.to_dict())
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
                                  'website': 'https://github.com/OCA/server-env'}},
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
                                   'website': 'https://github.com/OCA/server-env'}},
[...]
```
