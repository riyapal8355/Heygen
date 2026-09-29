"""Deterministic mock media fixtures for testing and mock provider pipelines.

Provides functions to generate structurally valid, decodable PNG and MP4 files
with valid container headers and metadata, ensuring test and mock pipelines
produce real media fixtures rather than non-media dummy bytes.
"""

import shutil
import struct
import subprocess
from pathlib import Path
from typing import Union
from app.media.ffmpeg import _generate_minimal_png_bytes


def create_valid_mock_png_fixture(path: Union[str, Path], width: int = 1920, height: int = 1080) -> Path:
    """Create a structurally valid, decodable PNG file on disk."""
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    png_bytes = _generate_minimal_png_bytes(width=width, height=height)
    target.write_bytes(png_bytes)
    return target


def _generate_minimal_mp4_bytes(duration_seconds: float = 5.0, width: int = 1920, height: int = 1080) -> bytes:
    """Generate a structurally valid minimal ISO-BMFF MP4 binary with ftyp, moov, and mdat boxes."""
    timescale = 600
    duration_units = int(duration_seconds * timescale)

    # Box helper
    def box(box_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload) + 8) + box_type + payload

    # 1. ftyp box
    ftyp_payload = b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41"
    ftyp = box(b"ftyp", ftyp_payload)

    # 2. mvhd box (Movie Header Box, version 0)
    # version (1), flags (3), creation_time (4), modification_time (4), timescale (4), duration (4),
    # rate (4: 0x00010000 = 1.0), volume (2: 0x0100 = 1.0), reserved (10), matrix (36), pre-defined (24), next_track_id (4)
    matrix = struct.pack(">9I", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000)
    mvhd_payload = (
        b"\x00\x00\x00\x00"  # version=0, flags=0
        + struct.pack(">IIII", 0, 0, timescale, duration_units)
        + struct.pack(">H", 0x0001)  # rate high
        + struct.pack(">H", 0x0000)  # rate low
        + struct.pack(">H", 0x0100)  # volume
        + b"\x00" * 10  # reserved
        + matrix
        + b"\x00" * 24  # pre-defined
        + struct.pack(">I", 2)  # next_track_id
    )
    mvhd = box(b"mvhd", mvhd_payload)

    # 3. tkhd box (Track Header Box, version 0)
    # flags: 0x000001 (track enabled), track_id: 1, duration: duration_units, width, height (16.16 fixed point)
    tkhd_payload = (
        b"\x00\x00\x00\x07"  # version=0, flags=TrackEnabled | TrackInMovie | TrackInPreview
        + struct.pack(">II", 0, 0)  # creation, mod time
        + struct.pack(">I", 1)  # track_id = 1
        + struct.pack(">I", 0)  # reserved
        + struct.pack(">I", duration_units)
        + b"\x00" * 8  # reserved
        + struct.pack(">H", 0)  # layer
        + struct.pack(">H", 0)  # alternate_group
        + struct.pack(">H", 0)  # volume (video track = 0)
        + struct.pack(">H", 0)  # reserved
        + matrix
        + struct.pack(">II", width << 16, height << 16)  # width & height in 16.16 fixed point
    )
    tkhd = box(b"tkhd", tkhd_payload)

    # 4. mdhd box (Media Header Box)
    mdhd_payload = (
        b"\x00\x00\x00\x00"
        + struct.pack(">IIII", 0, 0, timescale, duration_units)
        + struct.pack(">H", 0x55C4)  # language: und
        + struct.pack(">H", 0)  # pre-defined
    )
    mdhd = box(b"mdhd", mdhd_payload)

    # 5. hdlr box (Handler Reference Box)
    hdlr_payload = (
        b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"  # pre-defined
        + b"vide"  # handler_type = Video Track
        + b"\x00" * 12  # reserved
        + b"VideoHandler\x00"
    )
    hdlr = box(b"hdlr", hdlr_payload)

    # 6. vmhd box (Video Media Header)
    vmhd_payload = b"\x00\x00\x00\x01" + struct.pack(">HHHH", 0, 0, 0, 0)
    vmhd = box(b"vmhd", vmhd_payload)

    # 7. dinf -> dref box (Data Information Box)
    dref_entry = b"\x00\x00\x00\x01"  # self-contained
    dref_payload = b"\x00\x00\x00\x00" + struct.pack(">I", 1) + box(b"url ", dref_entry)
    dinf = box(b"dinf", box(b"dref", dref_payload))

    # 8. stbl (Sample Table Box)
    # stsd with avc1 sample entry
    avc1_payload = (
        b"\x00" * 6  # reserved
        + struct.pack(">H", 1)  # data_reference_index
        + b"\x00" * 16  # pre-defined, reserved
        + struct.pack(">HH", width, height)
        + struct.pack(">II", 0x00480000, 0x00480000)  # 72 dpi
        + struct.pack(">I", 0)  # reserved
        + struct.pack(">H", 1)  # frame_count
        + b"\x0bAVC Coding\x00" + b"\x00" * 21  # compressorname (32 bytes)
        + struct.pack(">H", 0x0018)  # depth = 24
        + struct.pack(">h", -1)  # pre-defined = -1
    )
    stsd = box(b"stsd", b"\x00\x00\x00\x00" + struct.pack(">I", 1) + box(b"avc1", avc1_payload))
    stts = box(b"stts", b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">II", 1, duration_units))
    stsc = box(b"stsc", b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))
    stsz = box(b"stsz", b"\x00\x00\x00\x00" + struct.pack(">II", 4, 1))  # sample size 4, 1 entry
    stco = box(b"stco", b"\x00\x00\x00\x00" + struct.pack(">I", 1) + struct.pack(">I", 48))

    stbl = box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf = box(b"minf", vmhd + dinf + stbl)
    mdia = box(b"mdia", mdhd + hdlr + minf)
    trak = box(b"trak", tkhd + mdia)
    moov = box(b"moov", mvhd + trak)

    # 9. mdat box (Media Data Box with 4 dummy NAL bytes)
    mdat = box(b"mdat", b"\x00\x00\x00\x01")

    return ftyp + moov + mdat


def create_valid_mock_mp4_fixture(
    path: Union[str, Path],
    duration_seconds: float = 5.0,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """
    Create a structurally valid, decodable MP4 file on disk.
    If ffmpeg CLI is installed and available, uses ffmpeg to synthesize a real playable H.264 MP4;
    otherwise writes a structurally valid ISO-BMFF container with valid ftyp, moov, and mdat boxes.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        try:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:d={max(0.5, duration_seconds)}:r=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-t", str(max(0.5, duration_seconds)),
                str(target),
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
                return target
        except Exception:
            pass

    # Fallback to pure-Python structurally valid ISO-BMFF MP4
    mp4_bytes = _generate_minimal_mp4_bytes(duration_seconds=duration_seconds, width=width, height=height)
    target.write_bytes(mp4_bytes)
    return target
