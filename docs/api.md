## files_file_create


## files_file_delete


## files_file_pin


## files_file_rename


## files_file_search

Search files.

This action is not stabilized yet and will change in future.

Provides an ability to search files using exact filter by name,
content_type, size, owner, etc. Results are paginated and returned in
package_search manner, as dict with `count` and `results` items.

All columns of File model can be used as filters. Before the search, type
of column and type of filter value are compared. If they are the same,
original values are used in search. If type different, column value and
filter value are casted to string.

This request produces `size = 10` SQL expression:
```sh
ckanapi action files_file_search size:10
```

This request produces `size::text = '10'` SQL expression:
```sh
ckanapi action files_file_search size=10
```

Even though results are usually not changed, using correct types leads to
more efficient search.

Apart from File columns, the following Owner properties can be used for
searching: `owner_id`, `owner_type`, `pinned`.

`storage_data` and `plugin_data` are dictionaries. Filter's value for these
fields used as a mask. For example, `storage_data={"a": {"b": 1}}` matches
any File with `storage_data` *containing* item `a` with value that contains
`b=1`. This works only with data represented by nested dictionaries,
without other structures, like list or sets.

Experimental feature: File columns can be passed as a pair of operator and
value. This feature will be replaced by strictly defined query language at
some point:

```sh
ckanapi action files_file_search size:'["<", 100]' content_type:'["like", "text/%"]'
```

Params:

* `start`: index of first row in result/number of rows to skip. Default: 0
* `rows`: number of rows to return. Default: 0
* `sort`: name of File column used for sorting. Default: name
* `reverse`: sort results in descending order. Default: false
* `storage_data`: mask for `storage_data` column. Default: {}
* `plugin_data`: mask for `plugin_data` column. Default: {}
* `owner_type: str`: show only specific owner id if present. Default: None
* `owner_type`: show only specific owner type if present. Default: None
* `pinned`: show only pinned/unpinned items if present. Default: None
## files_file_search_by_user

Internal action. Do not use it.
## files_file_show


## files_file_unpin


## files_multipart_complete


## files_multipart_refresh


## files_multipart_start


## files_multipart_update


## files_resource_upload


## files_transfer_ownership
