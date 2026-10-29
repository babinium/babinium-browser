# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import json
import tempfile

spec=importlib.util.spec_from_file_location('updater',Path(__file__).resolve().parents[1]/'scripts/filter-update.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)

class PreprocessorTest(unittest.TestCase):
    def test_capability_selects_scriptlet_instead_of_unavailable_html_filter(self):
        text='!#if cap_html_filtering\nexample.org##^script\n!#else\nexample.org##+js(json-prune, ads)\n!#endif\n'
        self.assertEqual(updater.preprocess(text),'example.org##+js(json-prune, ads)\n')
    def test_nested_webkit_branches(self):
        text='!#if !env_mv3\n!#if env_safari && (!env_mobile || env_firefox)\n||ads.test^\n!#else\nwrong\n!#endif\n!#endif\n'
        self.assertEqual(updater.preprocess(text),'||ads.test^\n')
    def test_reject_truncated_generation(self):
        for text in ['!#if env_safari\nx','!#else','!#endif','!#if a\n!#else\n!#else\n!#endif']:
            with self.subTest(text=text),self.assertRaises(ValueError):updater.preprocess(text)
    def test_unknown_include_cannot_silently_omit_rules(self):
        with self.assertRaises(ValueError):updater.preprocess('!#include missing.txt')
    def test_explicitly_enumerated_include_is_not_loaded_twice(self):
        self.assertEqual(updater.preprocess('||ad.test^\n!#include filters-2026.txt',{'filters-2026.txt'}),'||ad.test^\n')
    def test_failed_download_keeps_previous_generation(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);cache=base/'cache';data=base/'data';old=cache/'generation-old'
            old.mkdir(parents=True);data.mkdir();(old/'state.json').write_text('{}');(old/'engine.bin').write_bytes(b'previous index')
            (cache/'current').symlink_to(old.name)
            (data/'sources.json').write_text(json.dumps([{'file':'list.txt','url':'https://example.org/list.txt'}]))
            args=SimpleNamespace(cache=str(cache),data=str(data),compiler='/unneeded',force=True)
            with patch.object(updater,'fetch',side_effect=ValueError('invalid download')),self.assertRaises(ValueError):updater.update(args)
            self.assertEqual((cache/'current/engine.bin').read_bytes(),b'previous index')
            self.assertEqual(list(cache.glob('generation-*')),[old])

if __name__=='__main__':unittest.main()
