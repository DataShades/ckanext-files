try:
    from ckan.model import File
    from ckan.model import FileOwner as Owner
    from ckan.model import FileOwnerTransferHistory as TransferHistory
except ImportError:
    from .file import FilesFile as File
    from .owner import FilesOwner as Owner
    from .transfer_history import TransferHistory


__all__ = ["File", "Owner", "TransferHistory"]
