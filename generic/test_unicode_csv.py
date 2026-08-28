import io
import unittest

from generic.utils import unicode_csv


class UnicodeCsvTests(unittest.TestCase):
    def test_writer_preserves_utf8_export_bytes(self):
        output = io.BytesIO()

        writer = unicode_csv.Writer(output)
        writer.writerow(["Name", "caf\u00e9", b"plain", 42])
        writer.writerow(["Second", "row"])

        self.assertEqual(
            output.getvalue(),
            b"Name,caf\xc3\xa9,plain,42\r\nSecond,row\r\n",
        )

    def test_reader_decodes_source_encoding_to_text(self):
        source = io.BytesIO(b"Name,caf\xe9\r\n")

        rows = list(unicode_csv.Reader(source, encoding="latin-1"))

        self.assertEqual(rows, [["Name", "caf\u00e9"]])
