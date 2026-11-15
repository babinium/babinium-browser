"""Checks for automatic-caption cleanup and language choice without network access."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'bb_mpv_subtitles', Path(__file__).resolve().parents[1] / 'scripts/mpv-yt-dlp.py')
subtitles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subtitles)

ROLLING = '''1
00:00:00,000 --> 00:00:03,000
primera línea

2
00:00:02,000 --> 00:00:04,000
primera línea
segunda línea

3
00:00:04,000 --> 00:00:06,000
tercera línea
segunda línea
'''


class SubtitleTests(unittest.TestCase):
    def test_automatic_srt_removes_old_lines_and_truncates_overlaps(self):
        result = subtitles.clean_automatic_srt(ROLLING)
        self.assertEqual(result, '''WEBVTT

00:00:00.000 --> 00:00:02.000
primera línea

00:00:02.000 --> 00:00:04.000
segunda línea

00:00:04.000 --> 00:00:06.000
tercera línea
''')

    def test_invalid_subtitles_keep_the_original_track(self):
        track = {'ext': 'srt', 'data': 'no es un subtítulo válido'}
        self.assertIs(subtitles.clean_automatic_track(track, {}), track)

    def test_automatic_spanish_is_preferred_over_manual_other_language(self):
        info = {'subtitles': {'en': [{'ext': 'srt', 'data': 'English'}]},
                'automatic_captions': {'es': [{'ext': 'srt', 'data': ROLLING}]}}
        result = subtitles.select_subtitle(info)
        self.assertEqual(set(result), {'es'})
        self.assertEqual(result['es']['ext'], 'vtt')
        self.assertTrue(result['es']['data'].startswith('WEBVTT\n\n'))

    def test_manual_spanish_is_not_rewritten(self):
        track = {'ext': 'srt', 'data': ROLLING}
        info = {'subtitles': {'es': [track]},
                'automatic_captions': {'es': [{'ext': 'srt', 'data': ROLLING}]}}
        self.assertIs(subtitles.select_subtitle(info)['es'], track)

    def test_live_stream_keeps_the_original_automatic_track(self):
        track = {'ext': 'srt', 'data': ROLLING}
        info = {'is_live': True, 'automatic_captions': {'es': [track]}}
        with patch.object(subtitles, 'clean_automatic_track', side_effect=AssertionError('live')):
            self.assertIs(subtitles.select_subtitle(info)['es'], track)

    def test_fallback_language_when_spanish_is_absent(self):
        track = {'ext': 'srt', 'data': 'English'}
        self.assertIs(subtitles.select_subtitle({'subtitles': {'en': [track]}})['en'], track)

    def test_fixes_mislabeled_combined_format_on_original_spanish_video(self):
        fmt18 = {'format_id': '18', 'vcodec': 'avc1.42001E', 'acodec': 'mp4a.40.2',
                 'height': 360, 'ext': 'mp4', 'language': 'ar',
                 'url': 'https://rr4.googlevideo.com/videoplayback?itag=18&c=ANDROID'}
        info = {'language': 'es-US', 'format_id': '134+251-3',
                'requested_formats': [{'format_id': '134'}, {'format_id': '251-3'}],
                'formats': [fmt18]}
        self.assertTrue(subtitles.fix_original_spanish_combined_formats(info, prefer_combined_360=True))
        self.assertEqual(fmt18['language'], 'es-US')
        self.assertEqual(info['format_id'], '18')
        self.assertEqual(info['url'], fmt18['url'])
        self.assertNotIn('requested_formats', info)

    def test_keeps_combined_format_untouched_on_non_spanish_video(self):
        fmt18 = {'format_id': '18', 'vcodec': 'avc1.42001E', 'acodec': 'mp4a.40.2',
                 'language': 'en', 'url': 'https://rr4.googlevideo.com/videoplayback?itag=18&c=ANDROID'}
        info = {'language': 'en', 'formats': [fmt18]}
        self.assertFalse(subtitles.fix_original_spanish_combined_formats(info))
        self.assertEqual(fmt18['language'], 'en')


if __name__ == '__main__':
    unittest.main()
