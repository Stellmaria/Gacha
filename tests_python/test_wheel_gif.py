"""Offline geometry and renderer tests."""
import unittest
from scripts.wheel_gif import WEIGHTS, pointer_index, sector_center, target_angle


class WheelGifTests(unittest.TestCase):
    def test_weights_and_endpoints(self):
        self.assertEqual(sum(WEIGHTS), 100)
        for i in range(6):
            self.assertEqual(pointer_index(target_angle(i)), i)
            self.assertGreaterEqual(sector_center(i), 0)
            self.assertLess(sector_center(i), 360)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            target_angle(-1)
        with self.assertRaises(ValueError):
            target_angle(6)
        with self.assertRaises(ValueError):
            target_angle(2, 0)

    def test_render_if_pillow_installed(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow installed only for manual GitHub Actions smoke")
        import io
        from scripts.wheel_gif import render_wheel_gif
        for index in range(6):
            data = render_wheel_gif(index, size=240, frames=36)
            self.assertTrue(data.startswith(b"GIF89a"))
            self.assertLess(len(data), 8_000_000)
            im = Image.open(io.BytesIO(data))
            self.assertGreaterEqual(im.n_frames, 32)
            self.assertEqual(im.size, (240, 240))


if __name__ == "__main__":
    unittest.main()
