# Migration from native CKAN storage system

Important: ckanext-files itself is an independent file-management system. You
don't have to migrate existing files from groups, users and resources to
it. You can just start using ckanext-files for **new fields** defined in
metadata schema or for uploading arbitrary files. And continue using native
CKAN uploads for group/user images and resource files. Migration workflows
described here merely exist as a PoC of using ckanext-files for everything in
CKAN. Don't migrate your production instances yet, because concepts and rules
may change in future and migration process will change as well. Try migration
only as an experiment, that gives you an idea of what else you want to see in
ckanext-file, and share this idea with us.

Note: every migration workflow described below requires installed
ckanext-files. Complete [installation](../installation.md) section before going
further.

CKAN has following types of files:

* group/organization images
* user avatars
* resource files
* site logo
* files uploaded via custom logic from extensions

At the moment, there is no migration strategy for the last two types. Replacing
site logo manually is a trivial task, so there will be no dedicated command for
it. As for extensions, every of them is unique, so feel free to create an issue
in the current repository: we'll consider creation of migration script for your
scenario or, at least, explain how you can perform migration by yourself.

Migration process for group/organization/user images and resource uploads
described below. Keep in mind, that this process only describes migration from
native CKAN storage system, that keeps files inside local filesystem. If you
are using storage extensions, like
[ckanext-s3filestore](https://github.com/okfn/ckanext-s3filestore) or
[ckanext-cloudstorage](https://github.com/TkTech/ckanext-cloudstorage), create
an issue in the current repository with a request of migration command. As
there are a lot of different forks of such extension, creating reliable
migration script may be challenging, so we need some details about your
environment to help with migration.

Migration workflows bellow require certain changes to metadata schemas, UI
widgets for file uploads and styles of your portal(depending on the
customization).
