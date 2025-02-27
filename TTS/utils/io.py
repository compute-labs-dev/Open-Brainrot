from typing import Dict, Optional

import fsspec
import torch


def load_fsspec(
    path: str, map_location: Optional[torch.device] = None, **kwargs
) -> Dict:
    """Load checkpoint using fsspec for loading from remote locations.

    Args:
        path: Path to the checkpoint file.
        map_location: Location to load the checkpoint to.
        **kwargs: Keyword arguments to pass to torch.load.

    Returns:
        Loaded checkpoint.
    """
    with fsspec.open(path, "rb") as f:
        # Add weights_only=False to fix PyTorch 2.6 compatibility
        return torch.load(f, map_location=map_location, weights_only=False, **kwargs) 