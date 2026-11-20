"""Offline tests of ornate GIF assets, deterministic geometry and transparency."""
import io
import unittest

from scripts.ornate_wheel import ART_CENTERS, REVEAL_DELAY_SECONDS, art_index_at_pointer, art_target_angle, original_gifs_complete, render_ornate_gif
from scripts.wheel_gif import NAMES, WEIGHTS


class OrnateWheelTests(unittest.TestCase):
    def test_all_six_results_stop_at_the_pointer(self):
        self.assertEqual(len(ART_CENTERS), len(NAMES))
        self.assertEqual(sum(WEIGHTS), 100)
        for index in range(6):
            self.assertEqual(art_index_at_pointer(art_target_angle(index)), index)

    def test_animation_delay_is_longer_than_playback(self):
        self.assertGreater(REVEAL_DELAY_SECONDS, 5.94)

    def test_invalid_index_is_rejected(self):
        for i in (-1, 6, 10):
            with self.assertRaises(ValueError):
                art_target_angle(i)

    def test_all_six_animated_gifs_have_transparent_corners(self):
        try:
            from PIL import Image
            import cairosvg
        except ImportError:
            self.skipTest("GIF renderer dependencies installed only in gif-render-test")
        for index in range(6):
            data, duration = render_ornate_gif(index, size=240, frames=36)
            self.assertTrue(data.startswith(b"GIF89a"))
            self.assertLess(len(data), 8_000_000)
            self.assertGreater(duration, 5)
            self.assertLess(duration, 7)
            gif = Image.open(io.BytesIO(data))
            self.assertGreaterEqual(gif.n_frames, 32)
            self.assertEqual(gif.size, (240, 240))
            gif.seek(0)
            self.assertEqual(gif.convert("RGBA").getpixel((0, 0))[3], 0)
            gif.seek(gif.n_frames - 1)
            self.assertEqual(gif.convert("RGBA").getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
