import click

from ckan.plugins import toolkit as tk

import ckanext.files.config as files_conf

__all__ = [
    "files",
]


@click.group(short_help="ckanext-files CLI commands")
def files():
    pass


@files.command()
@click.option("--delete", "-d", is_flag=True, help="Delete orphaned datasets.")
@click.argument("threshold", required=False, type=int)
def remove_unused_files(delete: bool, threshold: int):
    """Remove files that are not used for N days. The unused threshold is specified
    in a config"""
    threshold = (
        threshold
        if threshold is not None
        else files_conf.get_unused_threshold()
    )

    files = tk.get_action("files_get_unused_files")(
        {"ignore_auth": True}, {"threshold": threshold}
    )

    if not files:
        return click.secho("No unused files", fg="blue")

    click.secho(
        f"Found unused files that were unused more than {threshold} days:", fg="green"
    )

    for file in files:
        click.echo(f"File path={file['path']}")

        if delete:
            tk.get_action("files_file_delete")(
                {"ignore_auth": True}, {"id": file["id"]}
            )
            click.echo(f"File was deleted", fg="red")

    if not delete:
        click.secho(
            "If you want to delete unused files, add `--delete` flag",
            fg="red",
        )
