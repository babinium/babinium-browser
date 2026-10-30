"""Exercise Babinium's actual format expression through yt-dlp, offline."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from mpv_format import selector


def video(name, height, codec='avc1.640028', audio='none', language=None):
    return {'format_id': name, 'url': 'https://example.invalid/' + name,
            'ext': 'mp4', 'height': height, 'width': round(height * 16 / 9),
            'vcodec': codec, 'acodec': audio, 'language': language, 'tbr': height * 2}


def audio(name, language, rate=128):
    return {'format_id': name, 'url': 'https://example.invalid/' + name,
            'ext': 'm4a', 'vcodec': 'none', 'acodec': 'mp4a.40.2',
            'language': language, 'abr': rate}


class MPVFormatTests(unittest.TestCase):
    def choose(self, formats):
        info = {'id': 'fixture', 'title': 'fixture', 'extractor': 'generic', 'formats': formats}
        with tempfile.TemporaryDirectory(prefix='bb-mpv-format-') as directory:
            path = Path(directory) / 'info.json'
            path.write_text(json.dumps(info))
            return subprocess.run(['yt-dlp', '--ignore-config', '--simulate', '--load-info-json',
                                   str(path), '--format', selector(), '--print', '%(format_id)s'],
                                  capture_output=True, text=True, timeout=20)

    def assert_choice(self, formats, expected):
        result = self.choose(formats)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)

    def test_prefers_1080_h264_and_spanish_audio_over_4k_and_english(self):
        self.assert_choice([video('4k', 2160, 'av01'), video('vp9', 1080, 'vp9'),
                            video('h264', 1080), video('720', 720),
                            audio('english', 'en', 256), audio('spanish', 'es-419')],
                           'h264+spanish')

    def test_uses_720_when_1080_is_missing(self):
        self.assert_choice([video('4k', 2160), video('720', 720),
                            audio('spanish', 'es'), audio('english', 'en')], '720+spanish')

    def test_prefers_1080_even_when_only_english_audio_exists(self):
        self.assert_choice([video('1080', 1080), video('720', 720), audio('english', 'en')],
                           '1080+english')

    def test_prefers_combined_spanish_audio_at_the_same_resolution(self):
        self.assert_choice([video('video', 1080), audio('english', 'en'),
                            video('combined-es', 1080, audio='mp4a.40.2', language='es')],
                           'combined-es')

    def test_uses_a_lower_resolution_when_720_and_1080_are_missing(self):
        self.assert_choice([video('4k', 2160), video('480', 480), audio('english', 'en')],
                           '480+english')

    def test_never_falls_back_to_4k(self):
        result = self.choose([video('4k', 2160), audio('english', 'en')])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Requested format is not available', result.stderr)

    def test_subtitle_filter_prevents_mpv_hook_from_loading_subtitles(self):
        header = (Path(__file__).resolve().parents[1] / 'src/mpv-options.h').read_text()
        self.assertIn('"--ytdl-raw-options=sub-langs=^$"', header)
        info = {'id': 'fixture', 'title': 'fixture', 'extractor': 'generic',
                'formats': [video('720', 720), audio('spanish', 'es')],
                'subtitles': {'es': [{'ext': 'srt', 'url': 'https://example.invalid/es.srt'}],
                              'en': [{'ext': 'srt', 'url': 'https://example.invalid/en.srt'}]}}
        with tempfile.TemporaryDirectory(prefix='bb-mpv-subs-') as directory:
            path = Path(directory) / 'info.json'
            path.write_text(json.dumps(info))
            def requested(languages):
                result = subprocess.run(['yt-dlp', '--ignore-config', '--simulate', '--load-info-json',
                    str(path), '--format', selector(), '--sub-langs', languages, '--write-srt',
                    '--dump-single-json'], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout).get('requested_subtitles') or {}
            self.assertEqual(set(requested('all')), {'es', 'en'})
            self.assertEqual(requested('^$'), {})


if __name__ == '__main__':
    unittest.main()
