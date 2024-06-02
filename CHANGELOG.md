# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## Unreleased

<small>[Compare with latest](https://github.com/DataShades/ckanext-files/compare/v0.3.1...HEAD)</small>

### Features

- add files_file_search action ([b8e8b4c](https://github.com/DataShades/ckanext-files/commit/b8e8b4c638ce4ae1159f47e7ccd62f021550b1e5) by Sergey Motornyuk).
- File.get method ([591ec48](https://github.com/DataShades/ckanext-files/commit/591ec48d4043caf486570faa4af586b11c31f6e9) by Sergey Motornyuk).
- get_storage without arguments returns default storage ([571e021](https://github.com/DataShades/ckanext-files/commit/571e021c44c4d719431c05a837bd6336b1896249) by Sergey Motornyuk).
- use timezone-aware date columns in model ([ae91cc7](https://github.com/DataShades/ckanext-files/commit/ae91cc79ae3b5e52098232fa9dc294c72942ea0d) by Sergey Motornyuk).

### Code Refactoring

- move hash, size, location(former filename) and content_type to the top level of file entity ([45a2679](https://github.com/DataShades/ckanext-files/commit/45a2679498a874ca6c2a00d154dd73a0bc394b29) by Sergey Motornyuk).
- extract File.completed==False into Multipart model ([d90d786](https://github.com/DataShades/ckanext-files/commit/d90d78684829291976a71384a49b40e66234386b) by Sergey Motornyuk).
- use dataclasses instead of dict in storage ([4965568](https://github.com/DataShades/ckanext-files/commit/4965568e22e7a36672c96a26e88e73c21f056730) by Sergey Motornyuk).
- storage_from_settings renamed to make_storage ([08fd767](https://github.com/DataShades/ckanext-files/commit/08fd76751ba1cb778a4c819613388be25bc099c6) by Sergey Motornyuk).
- transform combine_capabilities and exclude_capabilities into Capability methods ([73d32d4](https://github.com/DataShades/ckanext-files/commit/73d32d4d9f18b7e2b75fbf985eb29e73eed4183b) by Sergey Motornyuk).
- replace CapabilityCluster and CapabilityUnit with Capability ([16d3b7e](https://github.com/DataShades/ckanext-files/commit/16d3b7e39cee430e4ae2d2d48256a70827b4c26d) by Sergey Motornyuk).
- remove re-imported types from ckanext.files.types ([4b9e870](https://github.com/DataShades/ckanext-files/commit/4b9e870dcced1d3bffc39719dec8afcada96a913) by Sergey Motornyuk).
- remove support of CKAN pre v2.10 ([3e70bc2](https://github.com/DataShades/ckanext-files/commit/3e70bc27440a9c21560c50e3c744b247f2087e90) by Sergey Motornyuk).
- UnsupportedOperationError constructed with adapter type instead of name ([55d038d](https://github.com/DataShades/ckanext-files/commit/55d038d52e3dcfc09fb259122456079a197f4be8) by Sergey Motornyuk).

<!-- insertion marker -->
## [v0.3.1](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.1) - 2024-05-22

<small>[Compare with v0.3.0](https://github.com/DataShades/ckanext-files/compare/v0.3.0...v0.3.1)</small>

### Features

- generic_download view ([d000446](https://github.com/DataShades/ckanext-files/commit/d0004464f12ba76aac2531f33dad72247b1a62ca) by Sergey Motornyuk).

## [v0.3.0](https://github.com/DataShades/ckanext-files/releases/tag/v0.3.0) - 2024-05-16

<small>[Compare with v0.0.6](https://github.com/DataShades/ckanext-files/compare/v0.0.6...v0.3.0)</small>

### Features

- files_uploader plugin compatible with native uploader interface ([31aaaa6](https://github.com/DataShades/ckanext-files/commit/31aaaa676c3f1a0aba2bb3a706f85deb066895fa) by Sergey Motornyuk).

### Bug Fixes

- upload errors rendered outside of view box ([48005ed](https://github.com/DataShades/ckanext-files/commit/48005ed4229110dfca43fb219ba2bff4b8c9f5ba) by Sergey Motornyuk).
- upload errors in actions not tracked ([530c6d9](https://github.com/DataShades/ckanext-files/commit/530c6d98dcdb3e923c8eb2639cfef36e1b5e6d42) by Sergey Motornyuk).

### Code Refactoring

- disallow file creation via auth function ([0db289b](https://github.com/DataShades/ckanext-files/commit/0db289bfbbc3de99c3b49fbc671009db4406ccff) by Sergey Motornyuk).

## [v0.0.6](https://github.com/DataShades/ckanext-files/releases/tag/v0.0.6) - 2024-04-24

<small>[Compare with v0.2.6](https://github.com/DataShades/ckanext-files/compare/v0.2.6...v0.0.6)</small>

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
