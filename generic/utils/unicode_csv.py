# from http://docs.python.org/library/csv.html#csv-examples

import csv
import codecs
import io


class UTF8Recoder:
    """
    Iterator that reads and decodes an encoded byte stream.
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.reader)


class Reader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def __next__(self):
        return next(self.reader)

    def __iter__(self):
        return self

class Writer:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = io.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        def stringify(value):
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            elif hasattr(value, '__unicode__'):
                value = value.__unicode__()
            elif not isinstance(value, str):
                value = str(value)
            return value
        self.writer.writerow(map(stringify, row))
        # Fetch text output from the queue ...
        data = self.queue.getvalue()
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)
        self.queue.seek(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
