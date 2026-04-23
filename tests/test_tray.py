from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from simple_sticky_notes import tray


class TrayTests(unittest.TestCase):
    def test_load_icon_image_uses_resource_root_assets_path(self) -> None:
        app = mock.Mock()
        image_handle = mock.Mock()
        copied_image = object()
        image_handle.__enter__ = mock.Mock(return_value=image_handle)
        image_handle.__exit__ = mock.Mock(return_value=False)
        image_handle.copy.return_value = copied_image

        with mock.patch.object(tray, "resource_root", return_value=Path(r"C:\bundle\_internal")), mock.patch.object(
            tray.pystray, "Icon"
        ) as icon_factory, mock.patch.object(tray.Image, "open", return_value=image_handle) as open_image:
            tray.TrayController(app)

        open_image.assert_called_once_with(Path(r"C:\bundle\_internal\assets\icons\simple-sticky-notes-64.png"))
        icon_factory.assert_called_once()
        self.assertIs(icon_factory.call_args.args[1], copied_image)


if __name__ == "__main__":
    unittest.main()
