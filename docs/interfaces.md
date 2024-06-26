## Interfaces

ckanext-files registers `ckanext.files.shared.IFiles` interface. As extension
is actively developed, this interface may change in future. Always use
`inherit=True` when implementing `IFiles`.

```py
--8<-- "ckanext/files/interfaces.py:interface"
```
