# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [v1.0.0](https://github.com/DataShades/ckanext-files/releases/tag/v1.0.0) - 2025-07-12

<small>[Compare with v0.3.1](https://github.com/DataShades/ckanext-files/compare/v0.3.1...v1.0.0)</small>

### Features

- public_fs.public_root renamed to public_prefix ([e82c1e1](https://github.com/DataShades/ckanext-files/commit/e82c1e19b43239fed1567df0208d4c5d5cd37557) by Sergey Motornyuk).
- cascade access per storage ([8fe45e0](https://github.com/DataShades/ckanext-files/commit/8fe45e040f9c5bd42715acd98be0b78b516a3318) by Sergey Motornyuk).
- `storage clean` CLI command ([0642ddc](https://github.com/DataShades/ckanext-files/commit/0642ddc81326bc58bc44cc8b43b84d060b5f6439) by Sergey Motornyuk).
- `storage transfer` cli command ([4b8347f](https://github.com/DataShades/ckanext-files/commit/4b8347ff4761302723c3e2bc27200444920080d1) by Sergey Motornyuk).
- add link storage ([73e29bc](https://github.com/DataShades/ckanext-files/commit/73e29bcf7709fdb998e2436269a09738c698b46a) by Sergey Motornyuk).
- replace public link with permanent link ([dfb4a44](https://github.com/DataShades/ckanext-files/commit/dfb4a443c3f079dfe808bc4a8ad1cdbeb2f0cc24) by Sergey Motornyuk).
- redis storage uses `path` option instead of `prefix` ([d2173f2](https://github.com/DataShades/ckanext-files/commit/d2173f20b587dc40359dde9d0fdaaf42a2994fcc) by Sergey Motornyuk).
- `location_strategy: str` replaced with `location_transformers: [str]` ([d5671ec](https://github.com/DataShades/ckanext-files/commit/d5671eca432a2201586e05992134fe67234e90f3) by Sergey Motornyuk).
- transparent location strategy is enabled by default(use uuid for old behaviour) ([5bb414b](https://github.com/DataShades/ckanext-files/commit/5bb414b162bdcad7530557605f2fa5fd7535357a) by Sergey Motornyuk).
- add s3 backend ([d07abf9](https://github.com/DataShades/ckanext-files/commit/d07abf9248fcd623282fd887250342e085844b70) by Sergey Motornyuk).
- multipart complete has flags to keep data ([810ee4b](https://github.com/DataShades/ckanext-files/commit/810ee4b0596b4771662b037ecf4d4f73c803fc8b) by Sergey Motornyuk).
- fs storage update `uploaded` property of multipart via refresh action ([51427c6](https://github.com/DataShades/ckanext-files/commit/51427c69659784afda5c62b6e0781df6aaf35f43) by Sergey Motornyuk).
- user files list replaced by generic file list ([3d70bdd](https://github.com/DataShades/ckanext-files/commit/3d70bdd06036ac798441b4757b0df2174d8cad4b) by Sergey Motornyuk).
- add MULTIPART to redis storage ([e7aed27](https://github.com/DataShades/ckanext-files/commit/e7aed2756fe3fc6b46de1238ec3484ba03eb3849) by Sergey Motornyuk).
- files_file_replace action ([dcdd177](https://github.com/DataShades/ckanext-files/commit/dcdd177e6d5470b9a033711173cf0ae96ccad3c0) by Sergey Motornyuk).
- transfer_history table ([434abda](https://github.com/DataShades/ckanext-files/commit/434abda216b229c7cb69d171f24c0924ed22d1de) by Sergey Motornyuk).
- libcloud adapter ([6594bb9](https://github.com/DataShades/ckanext-files/commit/6594bb9ae60c3d0914d09116433069dc01352dc6) by Sergey Motornyuk).
- add SCAN and ANALYZE to redis storage ([96c2706](https://github.com/DataShades/ckanext-files/commit/96c2706a54bc462f1f1b6b933a5577ebc80c926a) by Sergey Motornyuk).
- pinned files ([3e1db60](https://github.com/DataShades/ckanext-files/commit/3e1db607fc275b25b246eb790f4144bab77d191a) by Sergey Motornyuk).
- files_download_info helper ([2659ae3](https://github.com/DataShades/ckanext-files/commit/2659ae3391ca6bfc254436743c5a960c20f2dc01) by Sergey Motornyuk).
- validators for file fields ([a849247](https://github.com/DataShades/ckanext-files/commit/a849247e9ac0f3cb0976ba51bcb593541e90d8be) by Sergey Motornyuk).
- add owner details to dictized file ([9ffd098](https://github.com/DataShades/ckanext-files/commit/9ffd09826f62f89a5b26c8314647aa137dd22f37) by Sergey Motornyuk).
- restrict list of available storage for authenticated uploads ([a075263](https://github.com/DataShades/ckanext-files/commit/a07526337bfcf266079ded9ffbfc469b03e2e98e) by Sergey Motornyuk).
- allow_authenticated_uploads config option ([7737b44](https://github.com/DataShades/ckanext-files/commit/7737b44eb0d62df6a6da9d6fdd614b3dbad5502f) by Sergey Motornyuk).
- implement temporal_link for fs ([45ec242](https://github.com/DataShades/ckanext-files/commit/45ec2426d6aa72b44fa0783fc43da94ae291707c) by Sergey Motornyuk).
- add public_link method to storage ([15a685b](https://github.com/DataShades/ckanext-files/commit/15a685bd0af977f9e537263ef403b7457fc739ba) by Sergey Motornyuk).
- optional hash verification for multipart upload ([28e5f69](https://github.com/DataShades/ckanext-files/commit/28e5f6952295afae401faa18fde9fdbb509211e8) by Sergey Motornyuk).
- add supported_types option for storages to restict upload types ([c5b43ac](https://github.com/DataShades/ckanext-files/commit/c5b43acabe11e2d5c94f5137df5948b0b29ea00c) by Sergey Motornyuk).
- add files_file_search action ([b8e8b4c](https://github.com/DataShades/ckanext-files/commit/b8e8b4c638ce4ae1159f47e7ccd62f021550b1e5) by Sergey Motornyuk).
- File.get method ([591ec48](https://github.com/DataShades/ckanext-files/commit/591ec48d4043caf486570faa4af586b11c31f6e9) by Sergey Motornyuk).
- get_storage without arguments returns default storage ([571e021](https://github.com/DataShades/ckanext-files/commit/571e021c44c4d719431c05a837bd6336b1896249) by Sergey Motornyuk).
- use timezone-aware date columns in model ([ae91cc7](https://github.com/DataShades/ckanext-files/commit/ae91cc79ae3b5e52098232fa9dc294c72942ea0d) by Sergey Motornyuk).

### Bug Fixes

- typing issues ([4d27781](https://github.com/DataShades/ckanext-files/commit/4d277816641b7232846bb0dfbec3c2bd8c521b6a) by Sergey Motornyuk).
- transfer_ownership validator now works with repeating subfields ([68fce8b](https://github.com/DataShades/ckanext-files/commit/68fce8be2079bb4559698edd01f05202b107f722) by Sergey Motornyuk).
- namespaced package cannot be discovered ([8d98ca6](https://github.com/DataShades/ckanext-files/commit/8d98ca6688a73a9586b606c17aeaef6d41d5f0ed) by Sergey Motornyuk).
- all auth functions work with anonymous user ([5c58a8b](https://github.com/DataShades/ckanext-files/commit/5c58a8b6c5b44cb3967dc6994bcee1b067a3a54b) by Sergey Motornyuk).
- auth function fail on anonymous request ([5cb0ca1](https://github.com/DataShades/ckanext-files/commit/5cb0ca1f8b1efd56f993ef5955d85655a5995b66) by Sergey Motornyuk).
- fix file upload manager styles ([b8225dc](https://github.com/DataShades/ckanext-files/commit/b8225dcde806e5f1db489d8ab20f7005edc329af) by mutantsan).
- connot complete upload because of cache ([95c41e7](https://github.com/DataShades/ckanext-files/commit/95c41e77ba0afc22140e4c086ed59e544882b48e) by Sergey Motornyuk).
- fix file item css style ([46bef83](https://github.com/DataShades/ckanext-files/commit/46bef831d5cf6e62c0390b455309e0b999b69d3f) by mutantsan).
- fix max file num bug ([bc46268](https://github.com/DataShades/ckanext-files/commit/bc46268b729e04b4d1b77d619b1b58ce190135be) by mutantsan).
- fixing multiple widget instance support, write doc strings ([a017b42](https://github.com/DataShades/ckanext-files/commit/a017b42be9e1fb0b2c9ef2de53dfe87983d28f29) by mutantsan).
- fix destroying the progress bar on fail ([61d15aa](https://github.com/DataShades/ckanext-files/commit/61d15aa20526b2b2257ef143de64e34d4905ee56) by mutantsan).
- fix display snippet word wrapping ([8b645f2](https://github.com/DataShades/ckanext-files/commit/8b645f2b2cbe09430641cee74a346d466d3624c6) by mutantsan).
- media file event hang if item doesn't exist yet ([d8c7a2a](https://github.com/DataShades/ckanext-files/commit/d8c7a2a8b2ccc0f6d216cd0b0149837b951d7d1f) by mutantsan).

### Code Refactoring

- extract implementations of adapters into file-keeper ([6bf7c6a](https://github.com/DataShades/ckanext-files/commit/6bf7c6aa8a8da8b4aff068f236327d6cc17f5582) by Sergey Motornyuk).
- redis storage: prefix renamed to path and now files kept inside hash ([8ec6996](https://github.com/DataShades/ckanext-files/commit/8ec6996948b52d39800a0581fe0f754697e270f1) by Sergey Motornyuk).
- Storage constructor accepts a single dictionary with settings ([285ddc7](https://github.com/DataShades/ckanext-files/commit/285ddc7d484b638e3e1bacca8f9c1b71a2e9c369) by Sergey Motornyuk).
- remove HashingReader.reset ([7e67d5f](https://github.com/DataShades/ckanext-files/commit/7e67d5f5df2c897debbd5b1cc7177d21cdca2673) by Sergey Motornyuk).
- do not allow str as upload source ([cae738d](https://github.com/DataShades/ckanext-files/commit/cae738d7203b9991425661c1c2d00ddb68fc2bd9) by Sergey Motornyuk).
- Capability.combine removed ([332c1a4](https://github.com/DataShades/ckanext-files/commit/332c1a422ae5bdd810e922f718ddf583e42601b8) by Sergey Motornyuk).
- access column removed from owner table and now only single owner allowed ([f8d385d](https://github.com/DataShades/ckanext-files/commit/f8d385d82f44696432fb4a28ce284ed19240ab49) by Sergey Motornyuk).
- add completed flag for rename, show and delete actions for simultaneous file and multipart support. ([10fb202](https://github.com/DataShades/ckanext-files/commit/10fb202a6e8c95dceee9a878a869812a84353219) by Sergey Motornyuk).
- rename files_upload_show to files_multipart_refresh ([ee2a4df](https://github.com/DataShades/ckanext-files/commit/ee2a4dfdddad4009636590a28b1d664dc321e42e) by Sergey Motornyuk).
- add kwargs to all Storage methods and extras to all service methods ([1526df1](https://github.com/DataShades/ckanext-files/commit/1526df10f566f02f70d1f0b88369fa5b69a3a815) by Sergey Motornyuk).
- rename Storage and Uploader *_multipart_upload into multipart_* for consistency with actions ([ddfd111](https://github.com/DataShades/ckanext-files/commit/ddfd11170286f463fe5115103b7357db106a6802) by Sergey Motornyuk).
- rename files_upload_* actions to files_multipart_*(initialize changed to start) ([6493a1d](https://github.com/DataShades/ckanext-files/commit/6493a1d5cb8225346d5414914d73a8ca3b9276b7) by Sergey Motornyuk).
- rename MULTIPART_UPLOAD capability to MULTIPART ([20d01bf](https://github.com/DataShades/ckanext-files/commit/20d01bf32eb52a91f734627664a2ab265238dcdb) by Sergey Motornyuk).
- use custom dataclass for Upload instead of werkzeug.datastructures.FileStorage ([78ae63b](https://github.com/DataShades/ckanext-files/commit/78ae63b79d63c095313af6e90a5c583f6d0678d6) by Sergey Motornyuk).
- move hash, size, location(former filename) and content_type to the top level of file entity ([45a2679](https://github.com/DataShades/ckanext-files/commit/45a2679498a874ca6c2a00d154dd73a0bc394b29) by Sergey Motornyuk).
- extract File.completed==False into Multipart model ([d90d786](https://github.com/DataShades/ckanext-files/commit/d90d78684829291976a71384a49b40e66234386b) by Sergey Motornyuk).
- use dataclasses instead of dict in storage ([4965568](https://github.com/DataShades/ckanext-files/commit/4965568e22e7a36672c96a26e88e73c21f056730) by Sergey Motornyuk).
- storage_from_settings renamed to make_storage ([08fd767](https://github.com/DataShades/ckanext-files/commit/08fd76751ba1cb778a4c819613388be25bc099c6) by Sergey Motornyuk).
- transform combine_capabilities and exclude_capabilities into Capability methods ([73d32d4](https://github.com/DataShades/ckanext-files/commit/73d32d4d9f18b7e2b75fbf985eb29e73eed4183b) by Sergey Motornyuk).
- replace CapabilityCluster and CapabilityUnit with Capability ([16d3b7e](https://github.com/DataShades/ckanext-files/commit/16d3b7e39cee430e4ae2d2d48256a70827b4c26d) by Sergey Motornyuk).
- remove re-imported types from ckanext.files.types ([4b9e870](https://github.com/DataShades/ckanext-files/commit/4b9e870dcced1d3bffc39719dec8afcada96a913) by Sergey Motornyuk).
- remove support of CKAN pre v2.10 ([3e70bc2](https://github.com/DataShades/ckanext-files/commit/3e70bc27440a9c21560c50e3c744b247f2087e90) by Sergey Motornyuk).
- UnsupportedOperationError constructed with adapter type instead of name ([55d038d](https://github.com/DataShades/ckanext-files/commit/55d038d52e3dcfc09fb259122456079a197f4be8) by Sergey Motornyuk).

## [v0.3.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.1) - 2024-05-22

<small>[Compare with v0.3.0](https://github.com/DataShades/ckanext-files/compare/v0.3.0...v0.3.1)</small>

### Features

- generic_download view ([d000446](https://github.com/DataShades/ckanext-files/commit/d0004464f12ba76aac2531f33dad72247b1a62ca) by Sergey Motornyuk).

## [v0.3.0](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.0) - 2024-05-16

<small>[Compare with v0.2.6](https://github.com/DataShades/ckanext-files/compare/v0.2.6...v0.3.0)</small>

### Features

- files_uploader plugin compatible with native uploader interface ([31aaaa6](https://github.com/DataShades/ckanext-files/commit/31aaaa676c3f1a0aba2bb3a706f85deb066895fa) by Sergey Motornyuk).

### Bug Fixes

- upload errors rendered outside of view box ([48005ed](https://github.com/DataShades/ckanext-files/commit/48005ed4229110dfca43fb219ba2bff4b8c9f5ba) by Sergey Motornyuk).
- upload errors in actions not tracked ([530c6d9](https://github.com/DataShades/ckanext-files/commit/530c6d98dcdb3e923c8eb2639cfef36e1b5e6d42) by Sergey Motornyuk).

### Code Refactoring

- disallow file creation via auth function ([0db289b](https://github.com/DataShades/ckanext-files/commit/0db289bfbbc3de99c3b49fbc671009db4406ccff) by Sergey Motornyuk).

## [v0.0.6](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.6) - 2024-04-24

<small>[Compare with v0.0.5](https://github.com/DataShades/ckanext-files/compare/v0.0.5...v0.0.6)</small>

### Bug Fixes

- declarations are missing from the package ([15fa97b](https://github.com/DataShades/ckanext-files/commit/15fa97b4c9fdaf6211f3e74e9cbf71eb19166a6b) by Sergey Motornyuk).

## [v0.2.6](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.6) - 2024-04-24

<small>[Compare with v0.2.4](https://github.com/DataShades/ckanext-files/compare/v0.2.4...v0.2.6)</small>

### Bug Fixes

- declarations are missing from the package ([16c4999](https://github.com/DataShades/ckanext-files/commit/16c499945740facc9f8f1c301fc088bbc78a81ab) by Sergey Motornyuk).
- catch permission error on delete ([9e6d799](https://github.com/DataShades/ckanext-files/commit/9e6d799417ec842cfea5b671446a91657e5fd6c9) by Sergey Motornyuk).

## [v0.2.4](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.4) - 2024-04-15

<small>[Compare with v0.2.3](https://github.com/DataShades/ckanext-files/compare/v0.2.3...v0.2.4)</small>

### Features

- add dropzone and immediate upload ([0486a00](https://github.com/DataShades/ckanext-files/commit/0486a007a3eb1178cb8e838160ac84579024fa68) by Sergey Motornyuk).

## [v0.2.3](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.3) - 2024-04-07

<small>[Compare with v0.2.2](https://github.com/DataShades/ckanext-files/compare/v0.2.2...v0.2.3)</small>

### Features

- file search by plugin data ([9dc51bd](https://github.com/DataShades/ckanext-files/commit/9dc51bd9f67f58d3f77aeff0247e9eb224ea0a38) by Sergey Motornyuk).
- multipart uploaders accept initialize/complete payloads in JS ([97d9933](https://github.com/DataShades/ckanext-files/commit/97d9933f69dd4fe4053912c75ba3db41e44c34e2) by Sergey Motornyuk).

### Bug Fixes

- python2 fails when content-length accessed ([6e99315](https://github.com/DataShades/ckanext-files/commit/6e993154d6988d3d144dad0790e9860daa0ab2b6) by Sergey Motornyuk).

## [v0.2.2](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.2) - 2024-03-18

<small>[Compare with v0.2.1](https://github.com/DataShades/ckanext-files/compare/v0.2.1...v0.2.2)</small>

## [v0.2.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.1) - 2024-03-18

<small>[Compare with v0.2.0](https://github.com/DataShades/ckanext-files/compare/v0.2.0...v0.2.1)</small>

### Features

- add move and copy operations ([577b537](https://github.com/DataShades/ckanext-files/commit/577b5377474afbdc9293655127dacdd4bc325b5b) by Sergey Motornyuk).

## [v0.2.0](https://github.com/DataShades/ckanext-files/releases/tag/v0.2.0) - 2024-03-12

<small>[Compare with v0.0.5](https://github.com/DataShades/ckanext-files/compare/v0.0.5...v0.2.0)</small>

### Features

- UI for file uploads ([4121e6f](https://github.com/DataShades/ckanext-files/commit/4121e6f530bfe7cf8bd77759a15e9e859886aa7c) by Sergey Motornyuk).
- redis storage ([cced1e8](https://github.com/DataShades/ckanext-files/commit/cced1e898666b14fd4f536405d42800cefa28640) by Sergey Motornyuk).
- multipart upload api ([96051d4](https://github.com/DataShades/ckanext-files/commit/96051d4b8449e6b7f96bf8e05a3860d972624326) by Sergey Motornyuk).
- GCS storage ([cc5ee76](https://github.com/DataShades/ckanext-files/commit/cc5ee76825748ea4988603c409a558d68bcb7434) by Sergey Motornyuk).
- split files into Storage and File ([71a7765](https://github.com/DataShades/ckanext-files/commit/71a7765304486f637a1d34b71c500a1bc8aaae04) by Sergey Motornyuk).

### Code Refactoring

- switch to typescript ([dfb5060](https://github.com/DataShades/ckanext-files/commit/dfb5060e1308c7de9600b0ac4f31aa7ee1bdbc10) by Sergey Motornyuk).
- full type coverage ([f399582](https://github.com/DataShades/ckanext-files/commit/f399582e2e9a6b6d612823b29709f52aaf45e887) by Sergey Motornyuk).
- get rid of blankets ([dfe901c](https://github.com/DataShades/ckanext-files/commit/dfe901c52b07111799793a7af7c37d0f9a024364) by Sergey Motornyuk).
- make types py2 compatible ([c099dfc](https://github.com/DataShades/ckanext-files/commit/c099dfc00534f11ab927406749e6503b509469a7) by Sergey Motornyuk).
- remove ckanext-toolbelt dependency ([dc885c7](https://github.com/DataShades/ckanext-files/commit/dc885c7a36e5f1d2103a58c7a4e5882e40bc7e77) by Sergey Motornyuk).

## [v0.0.5](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.5) - 2024-02-26

<small>[Compare with v0.0.4](https://github.com/DataShades/ckanext-files/compare/v0.0.4...v0.0.5)</small>

### Bug Fixes

- fix auth functions ([c76d5ff](https://github.com/DataShades/ckanext-files/commit/c76d5ffc0bde5731eb820bf9f4fb262965be5120) by mutantsan).
- collection type without generic ([0647355](https://github.com/DataShades/ckanext-files/commit/064735521fc9d704676e40f6199cbc6d1eefd208) by Sergey Motornyuk).

## [v0.0.4](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.4) - 2023-10-25

<small>[Compare with v0.0.2](https://github.com/DataShades/ckanext-files/compare/v0.0.2...v0.0.4)</small>

## [v0.0.2](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.2) - 2022-02-09

<small>[Compare with v0.0.1](https://github.com/DataShades/ckanext-files/compare/v0.0.1...v0.0.2)</small>

## [v0.0.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.1) - 2021-09-21

<small>[Compare with first commit](https://github.com/DataShades/ckanext-files/compare/d57d17e412821d56a9f5262636be89311e8050fc...v0.0.1)</small>
