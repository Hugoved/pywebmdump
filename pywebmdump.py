from __future__ import annotations
import argparse
import base64
import json
import os
import struct
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "1.1"
BANNER = "WebM/Matroska EBML Dumper - Python Version %s" % VERSION
MAX_PREVIEW_BYTES = 64
MAX_SCAN_ELEMENTS = 1_000_000
DEFAULT_METADATA_SCAN_BYTES = 8 * 1024 * 1024

ID_NAMES: Dict[int, str] = {
    0x1A45DFA3: "EBML", 0x4286: "EBMLVersion", 0x42F7: "EBMLReadVersion",
    0x42F2: "EBMLMaxIDLength", 0x42F3: "EBMLMaxSizeLength", 0x4282: "DocType",
    0x4287: "DocTypeVersion", 0x4285: "DocTypeReadVersion",
    0x18538067: "Segment", 0x114D9B74: "SeekHead", 0x4DBB: "Seek", 0x53AB: "SeekID", 0x53AC: "SeekPosition",
    0x1549A966: "Info", 0x2AD7B1: "TimecodeScale", 0x4489: "Duration", 0x4461: "DateUTC",
    0x4D80: "MuxingApp", 0x5741: "WritingApp", 0x73A4: "SegmentUID", 0x7384: "SegmentFilename",
    0x1654AE6B: "Tracks", 0xAE: "TrackEntry", 0xD7: "TrackNumber", 0x73C5: "TrackUID",
    0x83: "TrackType", 0xB9: "FlagEnabled", 0x88: "FlagDefault", 0x55AA: "FlagForced",
    0x9C: "FlagLacing", 0x6DE7: "MinCache", 0x6DF8: "MaxCache", 0x23E383: "DefaultDuration",
    0x234E7A: "DefaultDecodedFieldDuration", 0x23314F: "TrackTimecodeScale", 0x536E: "Name",
    0x22B59C: "Language", 0x22B59D: "LanguageIETF", 0x86: "CodecID", 0x63A2: "CodecPrivate",
    0x258688: "CodecName", 0x56AA: "CodecDelay", 0x56BB: "SeekPreRoll",
    0xE0: "Video", 0xB0: "PixelWidth", 0xBA: "PixelHeight", 0x54B0: "DisplayWidth", 0x54BA: "DisplayHeight",
    0x54B2: "DisplayUnit", 0x9A: "FlagInterlaced", 0x2EB524: "Colour", 0x55B0: "ColourMatrixCoefficients",
    0x55B1: "BitsPerChannel", 0x55B2: "ChromaSubsamplingHorz", 0x55B3: "ChromaSubsamplingVert",
    0x55B4: "CbSubsamplingHorz", 0x55B5: "CbSubsamplingVert", 0x55B6: "ChromaSitingHorz",
    0x55B7: "ChromaSitingVert", 0x55B8: "Range", 0x55B9: "TransferCharacteristics", 0x55BA: "Primaries",
    0x55BB: "MaxCLL", 0x55BC: "MaxFALL", 0x55D0: "MasteringMetadata", 0x55D1: "PrimaryRChromaticityX",
    0x55D2: "PrimaryRChromaticityY", 0x55D3: "PrimaryGChromaticityX", 0x55D4: "PrimaryGChromaticityY",
    0x55D5: "PrimaryBChromaticityX", 0x55D6: "PrimaryBChromaticityY", 0x55D7: "WhitePointChromaticityX",
    0x55D8: "WhitePointChromaticityY", 0x55D9: "LuminanceMax", 0x55DA: "LuminanceMin",
    0xE1: "Audio", 0xB5: "SamplingFrequency", 0x78B5: "OutputSamplingFrequency", 0x9F: "Channels", 0x6264: "BitDepth",
    0x6D80: "ContentEncodings", 0x6240: "ContentEncoding", 0x5031: "ContentEncodingOrder",
    0x5032: "ContentEncodingScope", 0x5033: "ContentEncodingType", 0x5034: "ContentCompression",
    0x4254: "ContentCompAlgo", 0x4255: "ContentCompSettings", 0x5035: "ContentEncryption",
    0x47E1: "ContentEncAlgo", 0x47E2: "ContentEncKeyID", 0x47E3: "ContentEncAESSettings",
    0x47E8: "AESSettingsCipherMode", 0x47E4: "ContentSignature", 0x47E5: "ContentSigKeyID",
    0x47E6: "ContentSigAlgo", 0x47E7: "ContentSigHashAlgo",
    0x1F43B675: "Cluster", 0xE7: "Timecode", 0xA3: "SimpleBlock", 0xA0: "BlockGroup", 0xA1: "Block",
    0x9B: "BlockDuration", 0xFB: "ReferenceBlock", 0xA4: "CodecState", 0x75A1: "BlockAdditions",
    0x1C53BB6B: "Cues", 0xBB: "CuePoint", 0xB3: "CueTime", 0xB7: "CueTrackPositions",
    0xF7: "CueTrack", 0xF1: "CueClusterPosition", 0x5378: "CueBlockNumber",
    0x1254C367: "Tags", 0x7373: "Tag", 0x63C0: "Targets", 0x67C8: "SimpleTag", 0x45A3: "TagName", 0x4487: "TagString",
    0x1043A770: "Chapters", 0x1941A469: "Attachments", 0xEC: "Void", 0xBF: "CRC-32",
}

MASTER_IDS = {
    0x1A45DFA3, 0x18538067, 0x114D9B74, 0x4DBB, 0x1549A966, 0x1654AE6B, 0xAE,
    0xE0, 0xE1, 0x2EB524, 0x55D0, 0x6D80, 0x6240, 0x5034, 0x5035, 0x47E3,
    0x1F43B675, 0xA0, 0x75A1, 0x1C53BB6B, 0xBB, 0xB7, 0x1254C367, 0x7373,
    0x63C0, 0x67C8, 0x1043A770, 0x1941A469,
}

UINT_IDS = {
    0x4286, 0x42F7, 0x42F2, 0x42F3, 0x4287, 0x4285, 0x2AD7B1, 0x53AC, 0xD7, 0x73C5,
    0x83, 0xB9, 0x88, 0x55AA, 0x9C, 0x6DE7, 0x6DF8, 0x23E383, 0x234E7A, 0x56AA,
    0x56BB, 0xB0, 0xBA, 0x54B0, 0x54BA, 0x54B2, 0x9A, 0x55B0, 0x55B1, 0x55B2,
    0x55B3, 0x55B4, 0x55B5, 0x55B6, 0x55B7, 0x55B8, 0x55B9, 0x55BA, 0x55BB,
    0x55BC, 0x9F, 0x6264, 0x5031, 0x5032, 0x5033, 0x4254, 0x47E1, 0x47E8, 0x47E6,
    0x47E7, 0xE7, 0x9B, 0xB3, 0xF7, 0xF1, 0x5378,
}
STRING_IDS = {0x4282, 0x4D80, 0x5741, 0x7384, 0x536E, 0x22B59C, 0x22B59D, 0x86, 0x258688, 0x45A3, 0x4487}
FLOAT_IDS = {0x4489, 0x23314F, 0xB5, 0x78B5, 0x55D1, 0x55D2, 0x55D3, 0x55D4, 0x55D5, 0x55D6, 0x55D7, 0x55D8, 0x55D9, 0x55DA}
BINARY_IDS = {0x73A4, 0x53AB, 0x63A2, 0x4255, 0x47E2, 0x47E4, 0x47E5, 0xA3, 0xA1, 0xA4, 0xBF}
SIGNED_IDS = {0xFB}

TRACK_TYPES = {1: "video", 2: "audio", 3: "complex", 0x10: "logo", 0x11: "subtitle", 0x12: "buttons", 0x20: "control", 0x21: "metadata"}
CONTENT_ENC_ALGOS = {0: "not encrypted", 1: "DES", 2: "3DES", 3: "Twofish", 4: "Blowfish", 5: "AES"}
AES_CIPHER_MODES = {1: "AES-CTR", 2: "AES-CBC"}
WEBM_ENCRYPTED_SIGNAL = 0x01
WEBM_PARTITIONED_SIGNAL = 0x02

class WebMDumpError(Exception):
    pass

@dataclass
class Element:
    id_value: int
    id_bytes: bytes
    size: Optional[int]
    size_len: int
    unknown_size: bool
    start: int
    header_size: int
    data_start: int
    data_end: int
    children: List["Element"] = field(default_factory=list)
    fields: Dict[str, Any] = field(default_factory=dict)
    children_skipped: bool = False
    error: Optional[str] = None

    @property
    def name(self) -> str:
        return ID_NAMES.get(self.id_value, "Unknown")

    @property
    def end(self) -> int:
        return self.data_end

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "name": self.name,
            "id": "0x%X" % self.id_value,
            "offset": self.start,
            "header_size": self.header_size,
            "size": self.size,
            "unknown_size": self.unknown_size,
        }
        if self.fields:
            out.update(self.fields)
        if self.children_skipped:
            out["children_skipped"] = True
        if self.error:
            out["error"] = self.error
        if self.children:
            out["children"] = [child.to_json() for child in self.children]
        return out

@dataclass
class WebMTrack:
    track_number: int = -1
    track_uid: Optional[int] = None
    track_type: Optional[int] = None
    codec_id: str = ""
    name: str = ""
    language: str = ""
    encrypted: bool = False
    enc_algo: Optional[int] = None
    aes_cipher_mode: Optional[int] = None
    key_id: bytes = b""


def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def read_metadata_prefix(path: str, limit: int = DEFAULT_METADATA_SCAN_BYTES) -> bytes:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        return f.read(min(size, max(4096, limit)))


def hex_preview(raw: bytes, limit: int = MAX_PREVIEW_BYTES) -> str:
    return raw.hex() if len(raw) <= limit else raw[:limit].hex() + "..."


def read_ebml_id(buf: bytes, off: int) -> Tuple[int, int, bytes]:
    if off >= len(buf):
        raise WebMDumpError("unexpected end while reading EBML ID")
    first = buf[off]
    mask = 0x80
    length = 1
    while length <= 4 and (first & mask) == 0:
        mask >>= 1
        length += 1
    if length > 4 or off + length > len(buf):
        raise WebMDumpError("invalid EBML ID")
    raw = buf[off:off + length]
    value = 0
    for b in raw:
        value = (value << 8) | b
    return value, length, raw


def read_ebml_size(buf: bytes, off: int) -> Tuple[Optional[int], int, bool]:
    if off >= len(buf):
        raise WebMDumpError("unexpected end while reading EBML size")
    first = buf[off]
    mask = 0x80
    length = 1
    while length <= 8 and (first & mask) == 0:
        mask >>= 1
        length += 1
    if length > 8 or off + length > len(buf):
        raise WebMDumpError("invalid EBML size")
    raw = buf[off:off + length]
    data_bits = 8 - length
    value = raw[0] & ((1 << data_bits) - 1)
    unknown = raw[0] == ((1 << data_bits) - 1) and all(b == 0xFF for b in raw[1:])
    for b in raw[1:]:
        value = (value << 8) | b
    return (None if unknown else value), length, unknown


def parse_uint(payload: bytes) -> int:
    value = 0
    for b in payload:
        value = (value << 8) | b
    return value


def parse_signed(payload: bytes) -> int:
    if not payload:
        return 0
    return int.from_bytes(payload, "big", signed=True)


def parse_string(payload: bytes) -> str:
    return payload.rstrip(b"\x00").decode("utf-8", "replace")


def parse_float(payload: bytes) -> Optional[float]:
    if len(payload) == 4:
        return struct.unpack(">f", payload)[0]
    if len(payload) == 8:
        return struct.unpack(">d", payload)[0]
    return None


def parse_vint_value(buf: bytes, off: int) -> Tuple[int, int, bytes]:
    if off >= len(buf):
        raise WebMDumpError("unexpected end while reading block track number")
    first = buf[off]
    mask = 0x80
    length = 1
    while length <= 8 and (first & mask) == 0:
        mask >>= 1
        length += 1
    if length > 8 or off + length > len(buf):
        raise WebMDumpError("invalid EBML VINT")
    value = first & (mask - 1)
    raw = buf[off:off + length]
    for i in range(1, length):
        value = (value << 8) | buf[off + i]
    return value, length, raw


def decode_block(payload: bytes) -> Dict[str, Any]:
    if len(payload) < 4:
        return {"payload_size": len(payload), "error": "block too small"}
    track_number, vint_len, _ = parse_vint_value(payload, 0)
    if len(payload) < vint_len + 3:
        return {"payload_size": len(payload), "error": "block header truncated"}
    relative_timecode = struct.unpack(">h", payload[vint_len:vint_len + 2])[0]
    flags = payload[vint_len + 2]
    frame_start = vint_len + 3
    signal = None
    encrypted = False
    partitioned = False
    iv = ""
    if len(payload) > frame_start:
        signal_byte = payload[frame_start]
        encrypted = bool(signal_byte & WEBM_ENCRYPTED_SIGNAL)
        partitioned = bool(signal_byte & WEBM_PARTITIONED_SIGNAL)
        if encrypted and len(payload) >= frame_start + 9:
            signal = signal_byte
            iv = payload[frame_start + 1:frame_start + 9].hex()
    return {
        "track_number": track_number,
        "relative_timecode": relative_timecode,
        "flags": flags,
        "keyframe": bool(flags & 0x80),
        "invisible": bool(flags & 0x08),
        "lacing": (flags >> 1) & 0x03,
        "discardable": bool(flags & 0x01),
        "payload_size": max(0, len(payload) - frame_start),
        "encrypted_signal": encrypted,
        "partitioned_signal": partitioned,
        "signal_byte": signal,
        "iv": iv,
    }


class WebMParser:
    def __init__(
        self,
        data: bytes,
        verbosity: int = 0,
        parse_clusters: bool = False,
        include_binary_base64: bool = False,
        include_block_data: bool = False,
    ) -> None:
        self.data = data
        self.verbosity = max(0, min(3, verbosity))
        self.parse_clusters = parse_clusters
        self.include_binary_base64 = include_binary_base64
        self.include_block_data = include_block_data
        self.elements: List[Element] = []

    def parse(self) -> List[Element]:
        self.elements = self._parse_children(0, len(self.data), None)
        return self.elements

    def _parse_children(self, start: int, end: int, parent: Optional[int]) -> List[Element]:
        children: List[Element] = []
        pos = start
        count = 0
        effective_end = min(end, len(self.data))
        while pos < effective_end and count < MAX_SCAN_ELEMENTS:
            count += 1
            try:
                elem = self._parse_one(pos, effective_end, parent)
            except Exception as exc:
                bad = Element(0, b"", 0, 0, False, pos, 0, pos, pos, error=str(exc))
                children.append(bad)
                break
            children.append(elem)
            if elem.end <= pos:
                break
            pos = elem.end
        return children

    def _parse_one(self, pos: int, parent_end: int, parent: Optional[int]) -> Element:
        id_value, id_len, id_raw = read_ebml_id(self.data, pos)
        size_value, size_len, unknown = read_ebml_size(self.data, pos + id_len)
        data_start = pos + id_len + size_len
        data_end = parent_end if size_value is None else min(data_start + size_value, parent_end)
        elem = Element(id_value, id_raw, size_value, size_len, unknown, pos, id_len + size_len, data_start, data_end)
        try:
            self._decode_element(elem)
            if elem.id_value in MASTER_IDS:
                if elem.id_value == 0x1F43B675 and not self.parse_clusters:
                    elem.children_skipped = True
                else:
                    elem.children = self._parse_children(elem.data_start, elem.data_end, elem.id_value)
        except Exception as exc:
            elem.error = str(exc)
        return elem

    def _decode_element(self, elem: Element) -> None:
        payload = self.data[elem.data_start:elem.data_end]
        if elem.id_value in MASTER_IDS:
            return
        if elem.id_value in UINT_IDS:
            value = parse_uint(payload)
            elem.fields["value"] = value
            if elem.id_value == 0x83:
                elem.fields["track_type_name"] = TRACK_TYPES.get(value, "unknown")
            elif elem.id_value == 0x47E1:
                elem.fields["algorithm_name"] = CONTENT_ENC_ALGOS.get(value, "unknown")
            elif elem.id_value == 0x47E8:
                elem.fields["cipher_mode_name"] = AES_CIPHER_MODES.get(value, "unknown")
        elif elem.id_value in SIGNED_IDS:
            elem.fields["value"] = parse_signed(payload)
        elif elem.id_value in STRING_IDS:
            elem.fields["value"] = parse_string(payload)
        elif elem.id_value in FLOAT_IDS:
            elem.fields["value"] = parse_float(payload)
        elif elem.id_value in BINARY_IDS:
            elem.fields["data_size"] = len(payload)
            if elem.id_value in {0xA3, 0xA1}:
                elem.fields.update(decode_block(payload))
                if self.include_block_data or self.verbosity >= 3:
                    elem.fields["data"] = hex_preview(payload)
                    if self.include_binary_base64:
                        elem.fields["data_base64"] = base64.b64encode(payload).decode("ascii")
            else:
                elem.fields["data"] = hex_preview(payload)
                if self.include_binary_base64:
                    elem.fields["data_base64"] = base64.b64encode(payload).decode("ascii")
        elif self.verbosity >= 2 and payload:
            elem.fields["data_size"] = len(payload)
            elem.fields["data"] = hex_preview(payload)

    def extract_tracks(self) -> Dict[int, WebMTrack]:
        if not self.elements:
            self.parse()
        tracks: Dict[int, WebMTrack] = {}
        for elem in walk_elements(self.elements):
            if elem.id_value == 0xAE:
                track = parse_track_entry(elem, self.data)
                if track.track_number > 0:
                    tracks[track.track_number] = track
        return tracks


def walk_elements(elements: Iterable[Element]) -> Iterable[Element]:
    for elem in elements:
        yield elem
        if elem.children:
            yield from walk_elements(elem.children)


def direct_child_value(parent: Element, child_id: int, data: bytes) -> Optional[bytes]:
    for child in parent.children:
        if child.id_value == child_id:
            return data[child.data_start:child.data_end]
    return None


def parse_track_entry(entry: Element, data: bytes) -> WebMTrack:
    track = WebMTrack()
    for child in entry.children:
        payload = data[child.data_start:child.data_end]
        if child.id_value == 0xD7:
            track.track_number = parse_uint(payload)
        elif child.id_value == 0x73C5:
            track.track_uid = parse_uint(payload)
        elif child.id_value == 0x83:
            track.track_type = parse_uint(payload)
        elif child.id_value == 0x86:
            track.codec_id = parse_string(payload)
        elif child.id_value == 0x536E:
            track.name = parse_string(payload)
        elif child.id_value == 0x22B59C:
            track.language = parse_string(payload)
        elif child.id_value == 0x6D80:
            for encodings_child in walk_elements([child]):
                if encodings_child.id_value == 0x5035:
                    track.encrypted = True
                elif encodings_child.id_value == 0x47E1:
                    track.enc_algo = parse_uint(data[encodings_child.data_start:encodings_child.data_end])
                elif encodings_child.id_value == 0x47E8:
                    track.aes_cipher_mode = parse_uint(data[encodings_child.data_start:encodings_child.data_end])
                elif encodings_child.id_value == 0x47E2:
                    track.key_id = data[encodings_child.data_start:encodings_child.data_end]
    return track


def track_to_json(track: WebMTrack) -> Dict[str, Any]:
    return {
        "track_number": track.track_number,
        "track_uid": track.track_uid,
        "track_type": track.track_type,
        "track_type_name": TRACK_TYPES.get(track.track_type, "unknown"),
        "codec_id": track.codec_id,
        "name": track.name,
        "language": track.language,
        "encrypted": track.encrypted,
        "content_enc_algo": track.enc_algo,
        "content_enc_algo_name": CONTENT_ENC_ALGOS.get(track.enc_algo, "unknown") if track.enc_algo is not None else None,
        "aes_cipher_mode": track.aes_cipher_mode,
        "aes_cipher_mode_name": AES_CIPHER_MODES.get(track.aes_cipher_mode, "unknown") if track.aes_cipher_mode is not None else None,
        "kid": track.key_id.hex() if track.key_id else None,
        "kid_base64": base64.b64encode(track.key_id).decode("ascii") if track.key_id else None,
    }


class TextPrinter:
    def __init__(self, verbosity: int = 0) -> None:
        self.verbosity = verbosity

    def print(self, elements: Iterable[Element]) -> None:
        for elem in elements:
            self._print_element(elem, 0)

    def _print_element(self, elem: Element, level: int) -> None:
        indent = "  " * level
        size = "unknown" if elem.unknown_size else str(elem.size)
        print(f"{indent}+ {elem.name} ({hex(elem.id_value)}) size={size} offset={elem.start}")
        for key, value in elem.fields.items():
            if self.verbosity == 0 and key in {"data", "data_base64"}:
                continue
            print(f"{indent}  {key}: {value}")
        if elem.children_skipped:
            print(f"{indent}  children: skipped (use --parse-clusters to expand Cluster blocks)")
        if elem.error:
            print(f"{indent}  error: {elem.error}")
        for child in elem.children:
            self._print_element(child, level + 1)


def is_webm_file(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == b"\x1a\x45\xdf\xa3"


def dump_webm(input_file: str, verbosity: int = 0) -> List[Element]:
    data = read_file(input_file)
    return WebMParser(data, verbosity=verbosity).parse()


def extract_webm_tracks(input_file: str) -> List[Dict[str, Any]]:
    data = read_metadata_prefix(input_file)
    parser = WebMParser(data, verbosity=1, parse_clusters=False)
    parser.parse()
    return [track_to_json(t) for _, t in sorted(parser.extract_tracks().items())]


def extract_webm_kids(input_file: str) -> List[str]:
    tracks = extract_webm_tracks(input_file)
    kids: List[str] = []
    for track in tracks:
        kid = track.get("kid")
        if kid and kid not in kids:
            kids.append(str(kid))
    return kids


def extract_first_webm_kid(input_file: str) -> Optional[str]:
    kids = extract_webm_kids(input_file)
    return kids[0] if kids else None


def extract_webm_content_encryption(input_file: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for track in extract_webm_tracks(input_file):
        if track.get("encrypted") or track.get("kid"):
            out.append({
                "track_number": track.get("track_number"),
                "track_type": track.get("track_type"),
                "track_type_name": track.get("track_type_name"),
                "codec_id": track.get("codec_id"),
                "encrypted": track.get("encrypted"),
                "content_enc_algo": track.get("content_enc_algo"),
                "content_enc_algo_name": track.get("content_enc_algo_name"),
                "aes_cipher_mode": track.get("aes_cipher_mode"),
                "aes_cipher_mode_name": track.get("aes_cipher_mode_name"),
                "kid": track.get("kid"),
            })
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pywebmdump.py",
        description="Python WebM/Matroska EBML dumper inspired by mp4dump style output.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("input", help="input WebM/Matroska file")
    p.add_argument("--verbosity", type=int, default=0, choices=[0, 1, 2, 3], help="detail level between 0 and 3")
    p.add_argument("--format", choices=["text", "json"], default="text", help="output format")
    p.add_argument("--no-banner", action="store_true", help="do not print the banner in text mode")
    p.add_argument("--tracks", action="store_true", help="print detected tracks only")
    p.add_argument("--extract-kids", action="store_true", help="print detected ContentEncKeyID/KID values, one per line")
    p.add_argument("--extract-first-kid", action="store_true", help="print only the first detected ContentEncKeyID/KID")
    p.add_argument("--extract-encryption", action="store_true", help="print compact ContentEncryption metadata as JSON")
    p.add_argument("--parse-clusters", action="store_true", help="expand Cluster children and Block/SimpleBlock entries (slow for full media files)")
    p.add_argument("--include-binary-base64", action="store_true", help="include base64 for binary EBML fields in JSON/text dumps")
    p.add_argument("--include-block-data", action="store_true", help="include block payload hex previews when Cluster parsing is enabled")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"ERROR: input file does not exist: {args.input}", file=sys.stderr)
        return 1
    try:
        if not is_webm_file(args.input):
            print("ERROR: input is not an EBML/WebM/Matroska file", file=sys.stderr)
            return 1
        if args.extract_kids:
            kids = extract_webm_kids(args.input)
            if not kids:
                print("ERROR: no WebM ContentEncKeyID/KID found", file=sys.stderr)
                return 1
            print("\n".join(kids))
            return 0
        if args.extract_first_kid:
            kid = extract_first_webm_kid(args.input)
            if kid is None:
                print("ERROR: no WebM ContentEncKeyID/KID found", file=sys.stderr)
                return 1
            print(kid)
            return 0
        if args.extract_encryption:
            print(json.dumps(extract_webm_content_encryption(args.input), indent=2, ensure_ascii=False))
            return 0
        if args.tracks:
            print(json.dumps(extract_webm_tracks(args.input), indent=2, ensure_ascii=False))
            return 0
        data = read_file(args.input) if args.parse_clusters else read_metadata_prefix(args.input)
        parser = WebMParser(
            data,
            verbosity=args.verbosity,
            parse_clusters=args.parse_clusters,
            include_binary_base64=args.include_binary_base64,
            include_block_data=args.include_block_data,
        )
        elements = parser.parse()
        if args.format == "json":
            print(json.dumps([e.to_json() for e in elements], indent=2, ensure_ascii=False))
        else:
            if not args.no_banner:
                print(BANNER)
                print()
            TextPrinter(args.verbosity).print(elements)
        return 0
    except (OSError, WebMDumpError, struct.error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())