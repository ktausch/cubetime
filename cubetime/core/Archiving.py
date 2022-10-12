from datetime import datetime
import logging
import os
import shutil
from typing import Dict, Optional

from cubetime.core.Config import global_config

logger = logging.getLogger(__name__)


def make_data_snapshot(filename: str, force: bool = False) -> None:
    """
    Makes a snapshot of the data directory.

    Args:
        filename: path to file to save. Must end if .tar.gz or .zip
        force: if True, overwrites file if it already exists
    """
    if os.path.exists(filename) and not force:
        raise FileExistsError(
            "Cannot save data snapshot because file already exists. "
            "Either move/delete existing file or set force flag."
        )
    extension_to_type: Dict[str, str] = {".tar.gz": "gztar", ".zip": "zip"}
    archive_type: Optional[str] = None
    for extension in extension_to_type:
        if filename[-len(extension) :] == extension:
            filename = filename[: -len(extension)]
            archive_type = extension_to_type[extension]
            break
    if archive_type is None:
        raise ValueError(
            "filename given to make_data_snapshot dit not have one of "
            f"the following extensions: {sorted(extension_to_type)}."
        )
    shutil.make_archive(filename, archive_type, global_config["data_directory"])
    timestamp = datetime.now().strftime(r"%H:%M:%S, %d %b, %Y")
    logger.info(f"Saved snapshot of data at {timestamp} to {filename}{extension}.")
    return
