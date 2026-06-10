import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from word_definitions import lookup_definitions, normalize_word, parse_definition_response


class WordDefinitionTests(unittest.TestCase):
    def test_parse_definition_response_groups_definitions_by_part_of_speech(self):
        payload = [
            {
                "word": "hello",
                "meanings": [
                    {
                        "partOfSpeech": "exclamation",
                        "definitions": [
                            {
                                "definition": "used as a greeting.",
                                "example": "hello there",
                                "synonyms": [],
                            }
                        ],
                    },
                    {
                        "partOfSpeech": "noun",
                        "definitions": [
                            {"definition": "an utterance of hello."},
                        ],
                    },
                ],
            }
        ]

        result = parse_definition_response(payload, "hello")

        self.assertEqual(result, {
            "word": "HELLO",
            "meanings": [
                {
                    "part_of_speech": "exclamation",
                    "definitions": [
                        {
                            "definition": "used as a greeting.",
                            "example": "hello there",
                        },
                    ],
                },
                {
                    "part_of_speech": "noun",
                    "definitions": [
                        {"definition": "an utterance of hello."},
                    ],
                },
            ],
        })

    def test_parse_definition_response_ignores_malformed_meanings(self):
        payload = [
            {
                "meanings": [
                    "not a meaning",
                    None,
                    {"partOfSpeech": "verb", "definitions": ["not a definition"]},
                    {"partOfSpeech": "noun", "definitions": None},
                    {"partOfSpeech": "", "definitions": [{"definition": "  "}]},
                    {
                        "definitions": [
                            {"definition": "a useful definition", "example": ""},
                        ],
                    },
                ],
            }
        ]

        result = parse_definition_response(payload, "word")

        self.assertEqual(result, {
            "word": "WORD",
            "meanings": [
                {
                    "part_of_speech": "unknown",
                    "definitions": [
                        {"definition": "a useful definition"},
                    ],
                },
            ],
        })

    def test_parse_definition_response_handles_unsupported_payload(self):
        result = parse_definition_response({"title": "No Definitions Found"}, "zzzz")

        self.assertEqual(result, {"word": "ZZZZ", "meanings": []})

    def test_lookup_definitions_handles_not_found_response(self):
        error = HTTPError(
            url="https://example.test",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

        with patch("word_definitions.urlopen", side_effect=error):
            result = lookup_definitions("zzzz")

        self.assertEqual(result, {"word": "ZZZZ", "meanings": []})

    def test_normalize_word_rejects_non_letters(self):
        with self.assertRaises(ValueError):
            normalize_word("hello!")


if __name__ == "__main__":
    unittest.main()
