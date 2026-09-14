import unittest

from analysis.text_completeness import abgeschnitten


class TextCompletenessTests(unittest.TestCase):
    def test_curly_closing_quote_is_terminal_punctuation(self):
        self.assertFalse(abgeschnitten('The answer ends normally.”'))

    def test_mid_sentence_ending_is_flagged(self):
        self.assertTrue(abgeschnitten("The answer ends in the middle of"))


if __name__ == "__main__":
    unittest.main()
