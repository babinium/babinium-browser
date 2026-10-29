# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import unittest

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

if __name__=='__main__':unittest.main()
