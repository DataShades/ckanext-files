
## [1.1.0a4](https://github.com/DataShades/ckanext-files/releases/tag/1.1.0a4) - 2026-01-22
[Compare with v1.1.0a3](https://github.com/DataShades/ckanext-files/compare/v1.1.0a3..1.1.0a4)

### 🐛 Bug Fixes

- public_fs fail on empty public path ([26dcd9b](https://github.com/DataShades/ckanext-files/commit/26dcd9bb2e3d35109b7a9dbd19b51274e306a82f))

## [v1.1.0a0](https://github.com/DataShades/ckanext-files/releases/tag/v1.1.0a0) - 2025-08-29
[Compare with v1.0.1](https://github.com/DataShades/ckanext-files/compare/v1.0.1..v1.1.0a0)

### 🚀 Features

- Multipart.upload sends sample to multipart_start ([dbd66ca](https://github.com/DataShades/ckanext-files/commit/dbd66ca771b480367ada3f24d7aff0bbe3e246a2))
- Reader.response that generates flask response ([26978f2](https://github.com/DataShades/ckanext-files/commit/26978f2a51ac1f1ebdedd255013535b563400fab))
- adapters CLI commands shows settings ([f187735](https://github.com/DataShades/ckanext-files/commit/f18773531baad3fe7d0159c5ab01f568e86097a7))

### 🐛 Bug Fixes

- file_create allows duplicates ([c217179](https://github.com/DataShades/ckanext-files/commit/c217179d8b4ae13ea721d2276f5e0bc067c4bde9))
- dispatch_download serves link instead of as_response ([66e5664](https://github.com/DataShades/ckanext-files/commit/66e56647ccb967aa0bc1c0063c2f012441fd2af2))

### 🚜 Refactor

- [**breaking**] drop multipart table ([ae8ac8e](https://github.com/DataShades/ckanext-files/commit/ae8ac8e57a1e2915cd7d3f7097e218a79b749ce7))
- [**breaking**] rewrite files_file_search ([ab270ee](https://github.com/DataShades/ckanext-files/commit/ab270eec4c66e5f5669ce3dbbbfc40c036efd1a4))
- [**breaking**] files_file_download auth renamed to files_permission_download_file ([03a200f](https://github.com/DataShades/ckanext-files/commit/03a200f2c30cf6ee78e125fcac2d9555635b1e97))
- [**breaking**] remove files_ensure_name validator ([1a0d9bd](https://github.com/DataShades/ckanext-files/commit/1a0d9bd0e7857ba41785b235766be98c6bbbf316))
- [**breaking**] `files_*_file` auth functions renamed to `files_permission_*_file` ([af28e04](https://github.com/DataShades/ckanext-files/commit/af28e047ff6a5e0e83315324a5a946041b8fc13f))
- [**breaking**] File.owner now contains relationship with Owner model ([41ae342](https://github.com/DataShades/ckanext-files/commit/41ae34283a68c087386cecfd0fee77574ae96507))
- [**breaking**] rename link capability ([48a796d](https://github.com/DataShades/ckanext-files/commit/48a796de5fa18d040d6c83490a1b811fa8589ef7))
- [**breaking**] remove MultipartData ([f4de2db](https://github.com/DataShades/ckanext-files/commit/f4de2db0dc96abb64452f46c557e3066c154bd32))
- [**breaking**] FS `create_path` option renamed to `initialize` ([f5dc4b4](https://github.com/DataShades/ckanext-files/commit/f5dc4b490a2bc70938a74b622609e8411b071a05))
- [**breaking**] add duration to temporal link ([4d38281](https://github.com/DataShades/ckanext-files/commit/4d38281c10d215c5647aecab92ea2df4cc320998))
- redis `path` option renamed to `bucket` ([1a9b917](https://github.com/DataShades/ckanext-files/commit/1a9b91768777c5c0533cc4f0a79c41b04702ce2a))
- TransferHistory: `leave_date` -> `at`, +`action` ([0663606](https://github.com/DataShades/ckanext-files/commit/0663606f3f6e70ffcd29e32540c787ac2efe2ce3))

### 📦 Dependencies

- [**breaking**] pin file-keeper to >=0.1.0 ([48754b3](https://github.com/DataShades/ckanext-files/commit/48754b379ca2d896f051066a242f8df95325d953))

## [v1.0.1](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.1) - 2025-07-13
[Compare with v1.0.0](https://github.com/DataShades/ckanext-files/compare/v1.0.0..v1.0.1)

### 🚀 Features

- set minimal file-keeper version to v0.0.10 ([edbf417](https://github.com/DataShades/ckanext-files/commit/edbf4174082511d84c58be7ea2b76e3ee225a038))
- add public_prefix(and permanent_link) to libcloud ([1c2571f](https://github.com/DataShades/ckanext-files/commit/1c2571fc78430c401ec4d53e70dae9110a63884e))

### 🐛 Bug Fixes

- actions do not pass upload-or-data to prepare_location ([e60b428](https://github.com/DataShades/ckanext-files/commit/e60b428160673c5512b2b9304412c88605c0f77c))

## [v1.0.0](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0) - 2025-07-12
[Compare with v1.0.0a9](https://github.com/DataShades/ckanext-files/compare/v1.0.0a9..v1.0.0)

### 🚀 Features

- [**breaking**] public_fs.public_root renamed to public_prefix ([e82c1e1](https://github.com/DataShades/ckanext-files/commit/e82c1e19b43239fed1567df0208d4c5d5cd37557))

### 🐛 Bug Fixes

- typing issues ([4d27781](https://github.com/DataShades/ckanext-files/commit/4d277816641b7232846bb0dfbec3c2bd8c521b6a))

## [v1.0.0a9](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a9) - 2025-04-04
[Compare with v1.0.0a8](https://github.com/DataShades/ckanext-files/compare/v1.0.0a8..v1.0.0a9)

### 🚀 Features

- cascade access per storage ([8fe45e0](https://github.com/DataShades/ckanext-files/commit/8fe45e040f9c5bd42715acd98be0b78b516a3318))
- `storage clean` CLI command ([0642ddc](https://github.com/DataShades/ckanext-files/commit/0642ddc81326bc58bc44cc8b43b84d060b5f6439))
- `storage transfer` cli command ([4b8347f](https://github.com/DataShades/ckanext-files/commit/4b8347ff4761302723c3e2bc27200444920080d1))
- add link storage ([73e29bc](https://github.com/DataShades/ckanext-files/commit/73e29bcf7709fdb998e2436269a09738c698b46a))
- replace public link with permanent link ([dfb4a44](https://github.com/DataShades/ckanext-files/commit/dfb4a443c3f079dfe808bc4a8ad1cdbeb2f0cc24))

### 📦 Dependencies

- set minimal version of file-keeper ([82c2113](https://github.com/DataShades/ckanext-files/commit/82c2113f5957bab91b949ac99e4022e59df51431))

## [v1.0.0a8](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a8) - 2025-03-19
[Compare with v1.0.0a7](https://github.com/DataShades/ckanext-files/compare/v1.0.0a7..v1.0.0a8)

### 🐛 Bug Fixes

- transfer_ownership validator now works with repeating subfields ([68fce8b](https://github.com/DataShades/ckanext-files/commit/68fce8be2079bb4559698edd01f05202b107f722))

## [v1.0.0a7](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a7) - 2025-03-18
[Compare with v1.0.0a6](https://github.com/DataShades/ckanext-files/compare/v1.0.0a6..v1.0.0a7)

### 🚀 Features

- [**breaking**] transparent location strategy is enabled by default(use uuid for old behaviour) ([5bb414b](https://github.com/DataShades/ckanext-files/commit/5bb414b162bdcad7530557605f2fa5fd7535357a))
- redis storage uses `path` option instead of `prefix` ([d2173f2](https://github.com/DataShades/ckanext-files/commit/d2173f20b587dc40359dde9d0fdaaf42a2994fcc))
- `location_strategy: str` replaced with `location_transformers: [str]` ([d5671ec](https://github.com/DataShades/ckanext-files/commit/d5671eca432a2201586e05992134fe67234e90f3))

### 🚜 Refactor

- extract implementations of adapters into file-keeper ([6bf7c6a](https://github.com/DataShades/ckanext-files/commit/6bf7c6aa8a8da8b4aff068f236327d6cc17f5582))

## [v1.0.0a6](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a6) - 2025-03-11
[Compare with v1.0.0a5](https://github.com/DataShades/ckanext-files/compare/v1.0.0a5..v1.0.0a6)

### 🐛 Bug Fixes

- namespaced package cannot be discovered ([8d98ca6](https://github.com/DataShades/ckanext-files/commit/8d98ca6688a73a9586b606c17aeaef6d41d5f0ed))

### 🚜 Refactor

- redis storage: prefix renamed to path and now files kept inside hash ([8ec6996](https://github.com/DataShades/ckanext-files/commit/8ec6996948b52d39800a0581fe0f754697e270f1))

### ❌ Removal

- ensure_option/prepare_settings are replaced with SettingsFactory ([73ccdd3](https://github.com/DataShades/ckanext-files/commit/73ccdd35d4b094d4689d7ddb3731cabf67a9a032))

## [v1.0.0a5](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a5) - 2025-03-05
[Compare with v1.0.0a3](https://github.com/DataShades/ckanext-files/compare/v1.0.0a3..v1.0.0a5)

### 🚀 Features

- add s3 backend ([d07abf9](https://github.com/DataShades/ckanext-files/commit/d07abf9248fcd623282fd887250342e085844b70))

### 🐛 Bug Fixes

- all auth functions work with anonymous user ([5c58a8b](https://github.com/DataShades/ckanext-files/commit/5c58a8b6c5b44cb3967dc6994bcee1b067a3a54b))
- auth function fail on anonymous request ([5cb0ca1](https://github.com/DataShades/ckanext-files/commit/5cb0ca1f8b1efd56f993ef5955d85655a5995b66))

## [v1.0.0a3](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a3) - 2024-09-18
[Compare with v1.0.0a2](https://github.com/DataShades/ckanext-files/compare/v1.0.0a2..v1.0.0a3)

### 🐛 Bug Fixes

- fix file upload manager styles ([b8225dc](https://github.com/DataShades/ckanext-files/commit/b8225dcde806e5f1db489d8ab20f7005edc329af))

## [v1.0.0a2](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a2) - 2024-08-31
[Compare with v1.0.0a1](https://github.com/DataShades/ckanext-files/compare/v1.0.0a1..v1.0.0a2)

### 🚀 Features

- multipart complete has flags to keep data ([810ee4b](https://github.com/DataShades/ckanext-files/commit/810ee4b0596b4771662b037ecf4d4f73c803fc8b))
- fs storage update `uploaded` property of multipart via refresh action ([51427c6](https://github.com/DataShades/ckanext-files/commit/51427c69659784afda5c62b6e0781df6aaf35f43))

### 🐛 Bug Fixes

- connot complete upload because of cache ([95c41e7](https://github.com/DataShades/ckanext-files/commit/95c41e77ba0afc22140e4c086ed59e544882b48e))

## [v1.0.0a1](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a1) - 2024-08-29
[Compare with v1.0.0a0](https://github.com/DataShades/ckanext-files/compare/v1.0.0a0..v1.0.0a1)

### 🚀 Features

- add toast support ([246577a](https://github.com/DataShades/ckanext-files/commit/246577ae0cb7c326a004d7342a677979f7cb7dfc))
- implement max file num, disable url, disable media, fix event handling ([49510ab](https://github.com/DataShades/ckanext-files/commit/49510abaf3c7ea553942786a0828c0c4c3a54f8f))
- implement file previews ([584f269](https://github.com/DataShades/ckanext-files/commit/584f269bdb73ff8bead1c060a5ae7a2133305128))

### 🐛 Bug Fixes

- fix file item css style ([46bef83](https://github.com/DataShades/ckanext-files/commit/46bef831d5cf6e62c0390b455309e0b999b69d3f))
- fix max file num bug ([bc46268](https://github.com/DataShades/ckanext-files/commit/bc46268b729e04b4d1b77d619b1b58ce190135be))
- fixing multiple widget instance support, write doc strings ([a017b42](https://github.com/DataShades/ckanext-files/commit/a017b42be9e1fb0b2c9ef2de53dfe87983d28f29))
- fix destroying the progress bar on fail ([61d15aa](https://github.com/DataShades/ckanext-files/commit/61d15aa20526b2b2257ef143de64e34d4905ee56))
- fix display snippet word wrapping ([8b645f2](https://github.com/DataShades/ckanext-files/commit/8b645f2b2cbe09430641cee74a346d466d3624c6))
- media file event hang if item doesn't exist yet ([d8c7a2a](https://github.com/DataShades/ckanext-files/commit/d8c7a2a8b2ccc0f6d216cd0b0149837b951d7d1f))

### 💼 Other

- change close button style ([0718aa7](https://github.com/DataShades/ckanext-files/commit/0718aa7f6c4e9d19cb1754e4728d69fcdd55c2ef))
- change image preview style ([80ddf94](https://github.com/DataShades/ckanext-files/commit/80ddf944950c8860cf69b8531d57b18c3a6235fa))

## [v1.0.0a0](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0a0) - 2024-07-02
[Compare with v0.3.1](https://github.com/DataShades/ckanext-files/compare/v0.3.1..v1.0.0a0)

### 🚀 Features

- user files list replaced by generic file list ([3d70bdd](https://github.com/DataShades/ckanext-files/commit/3d70bdd06036ac798441b4757b0df2174d8cad4b))
- add MULTIPART to redis storage ([e7aed27](https://github.com/DataShades/ckanext-files/commit/e7aed2756fe3fc6b46de1238ec3484ba03eb3849))
- files_file_replace action ([dcdd177](https://github.com/DataShades/ckanext-files/commit/dcdd177e6d5470b9a033711173cf0ae96ccad3c0))
- transfer_history table ([434abda](https://github.com/DataShades/ckanext-files/commit/434abda216b229c7cb69d171f24c0924ed22d1de))
- libcloud adapter ([6594bb9](https://github.com/DataShades/ckanext-files/commit/6594bb9ae60c3d0914d09116433069dc01352dc6))
- add SCAN and ANALYZE to redis storage ([96c2706](https://github.com/DataShades/ckanext-files/commit/96c2706a54bc462f1f1b6b933a5577ebc80c926a))
- pinned files ([3e1db60](https://github.com/DataShades/ckanext-files/commit/3e1db607fc275b25b246eb790f4144bab77d191a))
- files_download_info helper ([2659ae3](https://github.com/DataShades/ckanext-files/commit/2659ae3391ca6bfc254436743c5a960c20f2dc01))
- validators for file fields ([a849247](https://github.com/DataShades/ckanext-files/commit/a849247e9ac0f3cb0976ba51bcb593541e90d8be))
- add owner details to dictized file ([9ffd098](https://github.com/DataShades/ckanext-files/commit/9ffd09826f62f89a5b26c8314647aa137dd22f37))
- restrict list of available storage for authenticated uploads ([a075263](https://github.com/DataShades/ckanext-files/commit/a07526337bfcf266079ded9ffbfc469b03e2e98e))
- allow_authenticated_uploads config option ([7737b44](https://github.com/DataShades/ckanext-files/commit/7737b44eb0d62df6a6da9d6fdd614b3dbad5502f))
- implement temporal_link for fs ([45ec242](https://github.com/DataShades/ckanext-files/commit/45ec2426d6aa72b44fa0783fc43da94ae291707c))
- add public_link method to storage ([15a685b](https://github.com/DataShades/ckanext-files/commit/15a685bd0af977f9e537263ef403b7457fc739ba))
- optional hash verification for multipart upload ([28e5f69](https://github.com/DataShades/ckanext-files/commit/28e5f6952295afae401faa18fde9fdbb509211e8))
- add supported_types option for storages to restict upload types ([c5b43ac](https://github.com/DataShades/ckanext-files/commit/c5b43acabe11e2d5c94f5137df5948b0b29ea00c))
- add files_file_search action ([b8e8b4c](https://github.com/DataShades/ckanext-files/commit/b8e8b4c638ce4ae1159f47e7ccd62f021550b1e5))
- File.get method ([591ec48](https://github.com/DataShades/ckanext-files/commit/591ec48d4043caf486570faa4af586b11c31f6e9))
- get_storage without arguments returns default storage ([571e021](https://github.com/DataShades/ckanext-files/commit/571e021c44c4d719431c05a837bd6336b1896249))
- use timezone-aware date columns in model ([ae91cc7](https://github.com/DataShades/ckanext-files/commit/ae91cc79ae3b5e52098232fa9dc294c72942ea0d))

### 🚜 Refactor

- [**breaking**] remove support of CKAN pre v2.10 ([3e70bc2](https://github.com/DataShades/ckanext-files/commit/3e70bc27440a9c21560c50e3c744b247f2087e90))
- Storage constructor accepts a single dictionary with settings ([285ddc7](https://github.com/DataShades/ckanext-files/commit/285ddc7d484b638e3e1bacca8f9c1b71a2e9c369))
- remove HashingReader.reset ([7e67d5f](https://github.com/DataShades/ckanext-files/commit/7e67d5f5df2c897debbd5b1cc7177d21cdca2673))
- Capability.combine removed ([332c1a4](https://github.com/DataShades/ckanext-files/commit/332c1a422ae5bdd810e922f718ddf583e42601b8))
- do not allow str as upload source ([cae738d](https://github.com/DataShades/ckanext-files/commit/cae738d7203b9991425661c1c2d00ddb68fc2bd9))
- access column removed from owner table and now only single owner allowed ([f8d385d](https://github.com/DataShades/ckanext-files/commit/f8d385d82f44696432fb4a28ce284ed19240ab49))
- add completed flag for rename, show and delete actions for simultaneous file and multipart support. ([10fb202](https://github.com/DataShades/ckanext-files/commit/10fb202a6e8c95dceee9a878a869812a84353219))
- rename files_upload_show to files_multipart_refresh ([ee2a4df](https://github.com/DataShades/ckanext-files/commit/ee2a4dfdddad4009636590a28b1d664dc321e42e))
- add kwargs to all Storage methods and extras to all service methods ([1526df1](https://github.com/DataShades/ckanext-files/commit/1526df10f566f02f70d1f0b88369fa5b69a3a815))
- rename Storage and Uploader *_multipart_upload into multipart_* for consistency with actions ([ddfd111](https://github.com/DataShades/ckanext-files/commit/ddfd11170286f463fe5115103b7357db106a6802))
- rename files_upload_* actions to files_multipart_*(initialize changed to start) ([6493a1d](https://github.com/DataShades/ckanext-files/commit/6493a1d5cb8225346d5414914d73a8ca3b9276b7))
- rename MULTIPART_UPLOAD capability to MULTIPART ([20d01bf](https://github.com/DataShades/ckanext-files/commit/20d01bf32eb52a91f734627664a2ab265238dcdb))
- use custom dataclass for Upload instead of werkzeug.datastructures.FileStorage ([78ae63b](https://github.com/DataShades/ckanext-files/commit/78ae63b79d63c095313af6e90a5c583f6d0678d6))
- move hash, size, location(former filename) and content_type to the top level of file entity ([45a2679](https://github.com/DataShades/ckanext-files/commit/45a2679498a874ca6c2a00d154dd73a0bc394b29))
- extract File.completed==False into Multipart model ([d90d786](https://github.com/DataShades/ckanext-files/commit/d90d78684829291976a71384a49b40e66234386b))
- use dataclasses instead of dict in storage ([4965568](https://github.com/DataShades/ckanext-files/commit/4965568e22e7a36672c96a26e88e73c21f056730))
- storage_from_settings renamed to make_storage ([08fd767](https://github.com/DataShades/ckanext-files/commit/08fd76751ba1cb778a4c819613388be25bc099c6))
- transform combine_capabilities and exclude_capabilities into Capability methods ([73d32d4](https://github.com/DataShades/ckanext-files/commit/73d32d4d9f18b7e2b75fbf985eb29e73eed4183b))
- replace CapabilityCluster and CapabilityUnit with Capability ([16d3b7e](https://github.com/DataShades/ckanext-files/commit/16d3b7e39cee430e4ae2d2d48256a70827b4c26d))
- remove re-imported types from ckanext.files.types ([4b9e870](https://github.com/DataShades/ckanext-files/commit/4b9e870dcced1d3bffc39719dec8afcada96a913))
- UnsupportedOperationError constructed with adapter type instead of name ([55d038d](https://github.com/DataShades/ckanext-files/commit/55d038d52e3dcfc09fb259122456079a197f4be8))

### 📚 Documentation

- add migration guide for group and user images ([9ad0714](https://github.com/DataShades/ckanext-files/commit/9ad07144522f51a85064b47ab764e56a69aeb2f1))

## [v0.3.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.1) - 2024-05-22
[Compare with v0.3.0](https://github.com/DataShades/ckanext-files/compare/v0.3.0..v0.3.1)

### 🚀 Features

- generic_download view ([d000446](https://github.com/DataShades/ckanext-files/commit/d0004464f12ba76aac2531f33dad72247b1a62ca))

### 💼 Other

- add link methods to reader ([655700a](https://github.com/DataShades/ckanext-files/commit/655700ac22c7c40ca8c97e5dff443c28aa26a8ef))

## [v0.3.0](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.0) - 2024-05-16
[Compare with v0.0.6](https://github.com/DataShades/ckanext-files/compare/v0.0.6..v0.3.0)

### 🚀 Features

- files_uploader plugin compatible with native uploader interface ([31aaaa6](https://github.com/DataShades/ckanext-files/commit/31aaaa676c3f1a0aba2bb3a706f85deb066895fa))

### 🐛 Bug Fixes

- upload errors rendered outside of view box ([48005ed](https://github.com/DataShades/ckanext-files/commit/48005ed4229110dfca43fb219ba2bff4b8c9f5ba))
- upload errors in actions not tracked ([530c6d9](https://github.com/DataShades/ckanext-files/commit/530c6d98dcdb3e923c8eb2639cfef36e1b5e6d42))

### 🚜 Refactor

- disallow file creation via auth function ([0db289b](https://github.com/DataShades/ckanext-files/commit/0db289bfbbc3de99c3b49fbc671009db4406ccff))

## [v0.0.6](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.6) - 2024-04-24
[Compare with v0.2.6](https://github.com/DataShades/ckanext-files/compare/v0.2.6..v0.0.6)

### 🐛 Bug Fixes

- declarations are missing from the package ([15fa97b](https://github.com/DataShades/ckanext-files/commit/15fa97b4c9fdaf6211f3e74e9cbf71eb19166a6b))

## [v0.2.6](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.6) - 2024-04-24
[Compare with v0.2.4](https://github.com/DataShades/ckanext-files/compare/v0.2.4..v0.2.6)

### 🐛 Bug Fixes

- declarations are missing from the package ([16c4999](https://github.com/DataShades/ckanext-files/commit/16c499945740facc9f8f1c301fc088bbc78a81ab))
- catch permission error on delete ([9e6d799](https://github.com/DataShades/ckanext-files/commit/9e6d799417ec842cfea5b671446a91657e5fd6c9))

## [v0.2.4](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.4) - 2024-04-15
[Compare with v0.2.3](https://github.com/DataShades/ckanext-files/compare/v0.2.3..v0.2.4)

### 🚀 Features

- add dropzone and immediate upload ([0486a00](https://github.com/DataShades/ckanext-files/commit/0486a007a3eb1178cb8e838160ac84579024fa68))

## [v0.2.3](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.3) - 2024-04-07
[Compare with v0.2.2](https://github.com/DataShades/ckanext-files/compare/v0.2.2..v0.2.3)

### 🚀 Features

- file search by plugin data ([9dc51bd](https://github.com/DataShades/ckanext-files/commit/9dc51bd9f67f58d3f77aeff0247e9eb224ea0a38))
- multipart uploaders accept initialize/complete payloads in JS ([97d9933](https://github.com/DataShades/ckanext-files/commit/97d9933f69dd4fe4053912c75ba3db41e44c34e2))

### 🐛 Bug Fixes

- python2 fails when content-length accessed ([6e99315](https://github.com/DataShades/ckanext-files/commit/6e993154d6988d3d144dad0790e9860daa0ab2b6))

## [v0.2.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.1) - 2024-03-18
[Compare with v0.2.0](https://github.com/DataShades/ckanext-files/compare/v0.2.0..v0.2.1)

### 🚀 Features

- add move and copy operations ([577b537](https://github.com/DataShades/ckanext-files/commit/577b5377474afbdc9293655127dacdd4bc325b5b))

## [v0.2.0](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.0) - 2024-03-12
[Compare with v0.0.5](https://github.com/DataShades/ckanext-files/compare/v0.0.5..v0.2.0)

### 🚀 Features

- UI for file uploads ([4121e6f](https://github.com/DataShades/ckanext-files/commit/4121e6f530bfe7cf8bd77759a15e9e859886aa7c))
- redis storage ([cced1e8](https://github.com/DataShades/ckanext-files/commit/cced1e898666b14fd4f536405d42800cefa28640))
- multipart upload api ([96051d4](https://github.com/DataShades/ckanext-files/commit/96051d4b8449e6b7f96bf8e05a3860d972624326))
- GCS storage ([cc5ee76](https://github.com/DataShades/ckanext-files/commit/cc5ee76825748ea4988603c409a558d68bcb7434))
- split files into Storage and File ([71a7765](https://github.com/DataShades/ckanext-files/commit/71a7765304486f637a1d34b71c500a1bc8aaae04))

### 🚜 Refactor

- switch to typescript ([dfb5060](https://github.com/DataShades/ckanext-files/commit/dfb5060e1308c7de9600b0ac4f31aa7ee1bdbc10))
- full type coverage ([f399582](https://github.com/DataShades/ckanext-files/commit/f399582e2e9a6b6d612823b29709f52aaf45e887))
- get rid of blankets ([dfe901c](https://github.com/DataShades/ckanext-files/commit/dfe901c52b07111799793a7af7c37d0f9a024364))
- make types py2 compatible ([c099dfc](https://github.com/DataShades/ckanext-files/commit/c099dfc00534f11ab927406749e6503b509469a7))
- remove ckanext-toolbelt dependency ([dc885c7](https://github.com/DataShades/ckanext-files/commit/dc885c7a36e5f1d2103a58c7a4e5882e40bc7e77))

## [v0.0.5](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.5) - 2024-02-26
[Compare with v0.0.4](https://github.com/DataShades/ckanext-files/compare/v0.0.4..v0.0.5)

### 🚀 Features

- remove unused code ([ce0cad8](https://github.com/DataShades/ckanext-files/commit/ce0cad81202d43caa56e58a23eb6cedaacc33b04))
- implement file manager, part 2 ([7786655](https://github.com/DataShades/ckanext-files/commit/778665549f624b120ed58bd66fc3e92a44ef48ca))
- implement file manager, WIP ([733f90b](https://github.com/DataShades/ckanext-files/commit/733f90b1a42ae267e76bef4e88fdf9900dbb6a50))

### 🐛 Bug Fixes

- fix auth functions ([c76d5ff](https://github.com/DataShades/ckanext-files/commit/c76d5ffc0bde5731eb820bf9f4fb262965be5120))
- collection type without generic ([0647355](https://github.com/DataShades/ckanext-files/commit/064735521fc9d704676e40f6199cbc6d1eefd208))

### 💼 Other

- use signal to gather config sections ([9a8d0d5](https://github.com/DataShades/ckanext-files/commit/9a8d0d5c612c0e9963cad4302cfaa3992e518b24))

## [v0.0.4](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.4) - 2023-10-25
[Compare with v0.0.2](https://github.com/DataShades/ckanext-files/compare/v0.0.2..v0.0.4)

### 🚀 Features

- remove file from file system on remove file entity ([503deea](https://github.com/DataShades/ckanext-files/commit/503deea45b1c02709023f63df57e233116c6b0d7))

## [v0.0.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.1) - 2021-09-21
