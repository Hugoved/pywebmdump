# pywebmdump

**pywebmdump** is a Python-based tool for parsing, inspecting, and extracting data from **WebM / Matroska (EBML)** files.
It focuses on accurate element-level parsing, track metadata extraction, and encryption analysis for structured workflows.

---

## Features

* Full parsing of **WebM / Matroska EBML structure**
* Support for:

  * Segment, Tracks, Info, SeekHead
  * Cluster, Block, and SimpleBlock elements
* Detailed decoding of:

  * Track metadata (video, audio, subtitles)
  * EBML element types (UINT, STRING, FLOAT, BINARY)
  * Block-level structure (timecodes, flags, lacing)
* Built-in support for **encryption metadata**:

  * ContentEncodings / ContentEncryption
  * AES cipher modes (CTR / CBC)
  * Encryption flags inside blocks
* Extraction of:

  * **ContentEncKeyID (KID) (hex / base64)**
  * **Track-level encryption configuration**
* JSON and human-readable output modes
* Fast metadata scanning (without full cluster parsing)
* Optional deep parsing for full media inspection
* Stream-safe parsing for large files

---

## Requirements

* Python 3.9 or higher

No external dependencies required (standard library only).

---

## Usage

Basic dump:

```bash
python pywebmdump.py input.webm
```

With verbosity:

```bash
python pywebmdump.py input.webm --verbosity 2
```

JSON output:

```bash
python pywebmdump.py input.webm --format json
```

---

## Encryption / KID Extraction

Extract all KIDs:

```bash
python pywebmdump.py input.webm --extract-kids
```

Extract first KID only:

```bash
python pywebmdump.py input.webm --extract-first-kid
```

Extract encryption metadata:

```bash
python pywebmdump.py input.webm --extract-encryption
```

---

## Track Inspection

List detected tracks:

```bash
python pywebmdump.py input.webm --tracks
```

Example output:

```json
[
  {
    "track_number": 1,
    "track_type_name": "video",
    "codec_id": "V_VP9",
    "encrypted": true,
    "kid": "..."
  }
]
```

---

## Advanced Parsing

Enable full cluster parsing:

```bash
python pywebmdump.py input.webm --parse-clusters
```

Include binary data as base64:

```bash
python pywebmdump.py input.webm --include-binary-base64
```

Include block payload previews:

```bash
python pywebmdump.py input.webm --parse-clusters --include-block-data
```

---

## Python Usage

Basic WebM parsing:

```python
from pywebmdump import dump_webm

elements = dump_webm("input.webm", verbosity=1)

for elem in elements:
    print(elem.name, elem.start)
```

---

Extract structured track metadata:

```python
from pywebmdump import extract_webm_tracks

tracks = extract_webm_tracks("input.webm")

for track in tracks:
    print("Track:", track["track_number"])
    print("Type:", track["track_type_name"])
    print("Codec:", track["codec_id"])
    print("Encrypted:", track["encrypted"])
```

---

Extract all KIDs (ContentEncKeyID):

```python
from pywebmdump import extract_webm_kids

kids = extract_webm_kids("input.webm")

print("KIDs:", kids)
```

---

Extract first available KID:

```python
from pywebmdump import extract_first_webm_kid

kid = extract_first_webm_kid("input.webm")

print("First KID:", kid)
```

---

Extract encryption metadata:

```python
from pywebmdump import extract_webm_content_encryption

encryption = extract_webm_content_encryption("input.webm")

for entry in encryption:
    print("Track:", entry["track_number"])
    print("Encrypted:", entry["encrypted"])
    print("KID:", entry["kid"])
    print("Cipher:", entry["aes_cipher_mode_name"])
```

---

Low-level parser usage:

```python
from pywebmdump import read_file, WebMParser

data = read_file("input.webm")

parser = WebMParser(
    data,
    verbosity=2,
    parse_clusters=True,
    include_binary_base64=True
)

elements = parser.parse()

print(elements)
```

---

## Notes

This project is inspired by tools like **mp4dump (Bento4)**, but adapted for **WebM / Matroska (EBML)** and implemented fully in Python for flexibility and integration into custom workflows.

It is especially useful for:

* DRM analysis (WebM encryption / KID extraction)
* Media reverse engineering
* Automation pipelines (Widevine workflows)
* Inspecting WebM initialization metadata

---

## Limitations

* No media decryption is performed
* Full cluster parsing can be slow on large files
* Some uncommon EBML elements may not be fully decoded

---

## Issues and Support

If you encounter any issues, please open an issue in the repository.
Support and updates will be provided as time permits.

---

## Acknowledgements

Inspired by:

* Bento4 mp4dump
* Matroska / WebM specification
* EBML format specification
* DRM reverse engineering community
