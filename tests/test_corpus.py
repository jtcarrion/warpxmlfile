"""Byte-exact round-trip check over a local corpus of XML files.

Skipped unless ``--xml-corpus DIR`` is given. This is how the parser is
validated against many real Warp workflows without committing their data:

    pytest --xml-corpus ~/processing/bmp6/warp_tiltseries
"""

from __future__ import annotations

import warnings

import xmlfile
from xmlfile import XmlLossyContentWarning


def test_corpus_round_trips_byte_exactly(corpus_paths):
    failures = []
    for path in corpus_paths:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", XmlLossyContentWarning)
                doc = xmlfile.read(path)
            if xmlfile.to_string(doc) != path.read_text(encoding="utf-8"):
                failures.append(f"{path.name}: not byte-exact")
            for element in doc.root:
                if element.tag.startswith("Grid"):
                    rebuilt = xmlfile.array_to_grid(
                        xmlfile.grid_to_array(element),
                        element.tag,
                        margins=xmlfile.grid_margins(element),
                        template=element,
                    )
                    if rebuilt != element:
                        failures.append(f"{path.name}: {element.tag} not reproduced")
        except Exception as error:
            failures.append(f"{path.name}: {type(error).__name__}: {error}")

    assert not failures, (
        f"{len(failures)}/{len(corpus_paths)} files failed:\n  "
        + "\n  ".join(failures[:20])
    )
