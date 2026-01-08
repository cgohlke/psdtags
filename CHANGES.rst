Revisions
---------

2026.x.x

- Improve code quality.

2025.12.12

- Make boolean and optional parameters keyword-only (breaking).

2025.9.19

- Write MTrn key before layers (#17).

2025.9.15

- Add CAI, GENI, and OCIO keys.
- Drop support for Python 3.10.

2025.5.10

- Support Python 3.14.

2025.1.1

- Improve type hints.
- Support Python 3.13.

2024.5.24

- Fix docstring examples not correctly rendered on GitHub.

2024.2.22

- Fix reading PsdBoolean (#10).
- Fix order of PsdReferencePoint coordinates (breaking).
- Allow reading unaligned PsdLayer blending_ranges.

2024.1.15

- Fix multi-threading.

2024.1.8

- Add option to compress layer channels in multiple threads.
- Improve logging.
- Drop support for Python 3.9 and numpy < 1.23 (NEP29).

2023.8.24

- Fix channel data in layer and pattern blocks must be in big-endian order.

2023.6.15

- Use PsdThumbnailFormat enum for PsdThumbnailBlock.format.

2023.4.30

- Few API changes (breaking).
- Improve object repr.
- Drop support for Python 3.8 and numpy < 1.21 (NEP29).

2023.2.18

- Allow unknown PsdKeys (#5).

2023.2.8

- Change PsdPoint and PsdReferencePoint signatures (breaking).
- Add helper function to create composite from layers.

2022.8.25

- Update metadata.

2022.2.11

- Fix struct padding.
- Support TiffImageResources.

2022.2.2

- Various API changes (breaking).
- Handle additional layer information.
- Preserve structures of unknown format as opaque bytes.
- Add options to skip tag structures of unknown format.
- Add abstract base class for tag structures.
- Add classes for many structures.

2022.1.18

- Various API changes (breaking).
- Various fixes for writing TiffImageSourceData.
- Support filter masks.
- Add option to change channel compression on write.
- Warn when skipping ResourceKey sections.

2022.1.14

- Initial release.
