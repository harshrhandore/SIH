"""Bounded seed COPY helpers; table and column names come only from source constants."""

from itertools import islice


def copy_rows(conn, table, columns, rows):
    iterator = iter(rows)
    while True:
        batch = list(islice(iterator, 10000))
        if not batch:
            return
        with conn.cursor().copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
            for row in batch:
                copy.write_row(row)
