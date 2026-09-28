"""Byte-exact round-trip check over a local corpus of XML files.

Skipped unless ``--xml-corpus DIR`` is given. This is how the parser is
validated against many real Warp workflows without committing their data:

    pytest --xml-corpus ~/processing/bmp6/warp_tiltseries
"""

from __future__ import annotations

import warnings

from warpxmlfile import _convert as conv
from warpxmlfile import _xml as xmlfile
from warpxmlfile._xml import XmlLossyContentWarning


def test_corpus_round_trips_byte_exactly(corpus_paths):
    failures = []
    for path in corpus_paths:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", XmlLossyContentWarning)
                doc = xmlfile.read(path)
            if xmlfile.to_string(doc) != path.read_text(encoding="utf-8"):
                failures.append(f"{path.name}: not byte-exact")
            # the Warp model must reproduce an unedited file byte for byte
            import warpxmlfile

            if warpxmlfile.to_string(warpxmlfile.read(path)) != path.read_text(
                encoding="utf-8"
            ):
                failures.append(
                    f"{path.name}: WarpTiltSeries round trip not byte-exact"
                )
            for element in doc.root:
                if element.tag.startswith("Grid"):
                    rebuilt = conv.array_to_grid(
                        conv.grid_to_array(element),
                        element.tag,
                        margins=conv.grid_margins(element),
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
