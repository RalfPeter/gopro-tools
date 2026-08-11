#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gopro2gpmf.py
#  Version           : 2.0
#  Beschreibung      : Keine Beschreibung verfügbar.
#  Zeilen            : 387
#  Abhängigkeiten    : hashlib, pathlib, struct
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    ceil4(int)                                           → Rundet n auf das nächste Vielfache von 4 auf.
#    read_devc_block_size(bytes, int)                     → Return total length of a DEVC block starting at pos, or 0 if invalid.
#    extract_devc(str, bool, bool)                        → Extract DEVC devc_lists from a (possibly broken) GoPro file by GPMF header math.
#    extract_gpmd_chunks(Path, Path)                      → Kurzbeschreibung für extract_gpmd_chunks.
#    parse_gpmf_element(bytes, int)                       → Liest ein GPMF-Element ab offset und gibt seine Gesamtlänge zurück.
#    extract_devc_raw(Path, Path)                         → Kurzbeschreibung für extract_devc_raw.
#    make_gpmf_atom(Path, bytes)                          → Kurzbeschreibung für make_gpmf_atom.
#    make_udta_with_gpmf(Path, bytes)                     → GPMF Atom
#    extract_devc_clean(Path, Path)                       → DEVC-Blöcke extrahieren, kaputte und doppelte Blöcke filtern.
#    create_mp4_with_gpmf(str, devc_source, str)          → Fügt einen GPMF-Track zu einem reparierten Video hinzu.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import struct
import hashlib
from pathlib import Path


# --------------------------------------------------------------------------------
def ceil4(n: int) -> int:
    """Rundet n auf das nächste Vielfache von 4 auf.
    
    :param n: (int) Beschreibung von n.
    :return: (int) Beschreibung des Rückgabewerts.
    """

    return (((n - 1) >> 2) + 1) << 2


# --------------------------------------------------------------------------------
def read_devc_block_size(data: bytes, pos: int) -> int:
    """Return total length of a DEVC block starting at pos, or 0 if invalid.
    
    :param data: (bytes) Beschreibung von data.
    :param pos: (int) Beschreibung von pos.
    :return: (int) Beschreibung des Rückgabewerts.
    """

    if pos + 8 > len(data):
        return 0

    fourcc, typec, size, repeat = struct.unpack_from(">4sBBH", data, pos)
    if fourcc != b"DEVC":
        return 0

    payload_len = ceil4(size * repeat)
    block_size = 8 + payload_len

    if payload_len < 0 or block_size <= 8 or pos + block_size > len(data):
        return 0

    return block_size


# --------------------------------------------------------------------------------
def extract_devc(file_path: str, clean: bool = True, join: bool = True) -> bytes | list[bytes]:
    """Extract DEVC devc_lists from a (possibly broken) GoPro file by GPMF header math.
    
    :param file_path: (str) Beschreibung von file_path.
    :param clean: (bool) Beschreibung von clean.
    :param join: (bool) Beschreibung von join.
    :return: (bytes | list[bytes]) Beschreibung des Rückgabewerts.
    """

    fd = Path(file_path)
    data = fd.read_bytes()

    devc_lists: list[bytes] = []
    seen: set[str] = set() if clean else set()

    pos = 0
    while True:
        pos = data.find(b"DEVC", pos)
        if pos == -1:
            break

        size = read_devc_block_size(data, pos)
        if size == 0:
            # Kein valider Header an dieser Stelle -> weiter suchen
            pos = pos + 1
            continue

        block = data[pos: pos + size]

        if clean:
            h = hashlib.sha1(block).hexdigest()
            if h in seen:
                pos = pos + size
                continue
            seen.add(h)

        devc_lists.append(block)
        pos = pos + size

    if join:
        return b"".join(devc_lists)

    return devc_lists


# --------------------------------------------------------------------------------
def extract_gpmd_chunks(file: Path, out_file: Path):
    """Kurzbeschreibung für extract_gpmd_chunks.
    
    :param file: (Path) Beschreibung von file.
    :param out_file: (Path) Beschreibung von out_file.
    """

    with open(file, "rb") as fd:
        data = fd.read()

    signature = b'gpmd'
    pos = 0
    chunks = []

    while True:
        pos = data.find(signature, pos)
        if pos == -1:
            break
        # Atom-Größe ist 4 Bytes vor 'gpmd'
        size = int.from_bytes(data[pos-4:pos], "big")
        chunk = data[pos-4:pos+size]
        chunks.append(chunk)
        pos += size

    with open(out_file, "wb") as out:
        for c in chunks:
            out.write(c)

    print(f"{len(chunks)} GPMF-Chunks extrahiert -> {out_file}")


# --------------------------------------------------------------------------------
def parse_gpmf_element(data: bytes, offset: int) -> int:
    """Liest ein GPMF-Element ab offset und gibt seine Gesamtlänge zurück.
    
    :param data: (bytes) Beschreibung von data.
    :param offset: (int) Beschreibung von offset.
    :return: (int) Beschreibung des Rückgabewerts.
    """

    if offset + 8 > len(data):
        return 0  # unvollständig

    fourcc, typec, size, repeat = struct.unpack_from(">4sBBH", data, offset)
    payload_len = ceil4(size * repeat)
    total_len = 8 + payload_len
    return total_len


# --------------------------------------------------------------------------------
def extract_devc_raw(file: Path, out_file: Path):
    """Kurzbeschreibung für extract_devc_raw.
    
    :param file: (Path) Beschreibung von file.
    :param out_file: (Path) Beschreibung von out_file.
    """

    with open(file, "rb") as fd:
        data = fd.read()
    print(f"Dateilänge: {len(data)}")

    signature = b"DEVC"
    pos, i = 0, 0
    devc_lists = []

    while True:
        pos = data.find(signature, pos)
        if pos == -1:
            break

        # FourCC + Type + Size + Repeat an dieser Stelle lesen
        if pos + 8 > len(data):
            break

        fourcc, typec, size, repeat = struct.unpack_from(">4sBBH", data, pos)
        payload_len = ceil4(size * repeat)
        block_size = 8 + payload_len  # inkl. Header

        # Sicherheit: Dateiende?
        if pos + block_size > len(data):
            break

        block = data[pos:pos+block_size]
        devc_lists.append(block)

        i += 1
        print(f"{i:5}: Position: {pos}, Blockgröße: {block_size}")

        pos += block_size  # nächster Block

    with open(out_file, "wb") as out:
        for j, d in enumerate(devc_lists, 1):
            out.write(d)
            print(f"Block {j:5}/{i:5} geschrieben")

    print(f"{len(devc_lists)} DEVC-Blöcke extrahiert -> {out_file}")


# --------------------------------------------------------------------------------
def make_gpmf_atom(file: Path, gpmf_bytes: bytes):
    """Kurzbeschreibung für make_gpmf_atom.
    
    :param file: (Path) Beschreibung von file.
    :param gpmf_bytes: (bytes) Beschreibung von gpmf_bytes.
    """

    size = 8 + len(gpmf_bytes)
    temp_gpmf = size.to_bytes(4, 'big') + b'GPMF' + gpmf_bytes

    with open(file, "wb") as fd:
        fd.write(temp_gpmf)


# --------------------------------------------------------------------------------
def make_udta_with_gpmf(file: Path, gpmf_bytes: bytes):
    # GPMF Atom
    """GPMF Atom
    
    :param file: (Path) Beschreibung von file.
    :param gpmf_bytes: (bytes) Beschreibung von gpmf_bytes.
    """

    gpmf_size = 8 + len(gpmf_bytes)
    gpmf_atom = gpmf_size.to_bytes(4, "big") + b"GPMF" + gpmf_bytes

    # UDTA Atom drumherum
    udta_size = 8 + len(gpmf_atom)
    udta_atom = udta_size.to_bytes(4, "big") + b"udta" + gpmf_atom

    # Datei schreiben
    file.write_bytes(udta_atom)


# --------------------------------------------------------------------------------
def extract_devc_clean(file: Path, out_file: Path):
    """DEVC-Blöcke extrahieren, kaputte und doppelte Blöcke filtern.
    
    :param file: (Path) Beschreibung von file.
    :param out_file: (Path) Beschreibung von out_file.
    """

    with open(file, "rb") as fd:
        data = fd.read()
    print(f"Dateilänge: {len(data)} Bytes")

    signature = b"DEVC"
    pos = 0
    devc_lists = []
    seen_offsets = set()  # vermeidet doppelte Blöcke

    while True:
        pos = data.find(signature, pos)
        if pos == -1 or pos + 8 > len(data):
            break

        # FourCC, Type, Size, Repeat auslesen
        try:
            fourcc, typec, size, repeat = struct.unpack_from(">4sBBH", data, pos)
        except struct.error:
            pos += 4
            continue

        payload_len = ceil4(size * repeat)
        block_size = 8 + payload_len

        # Sicherheit: Block passt in die Datei?
        if pos + block_size > len(data):
            pos += 4
            continue

        # Block nur einmal aufnehmen
        if pos in seen_offsets:
            pos += block_size
            continue
        seen_offsets.add(pos)

        block = data[pos:pos+block_size]
        devc_lists.append(block)
        pos += block_size

    # In Datei schreiben
    with open(out_file, "wb") as out:
        for i, d in enumerate(devc_lists, 1):
            out.write(d)
            print(f"Block {i:5}/{len(devc_lists):5} geschrieben (Größe {len(d)})")

    print(f"{len(devc_lists)} DEVC-Blöcke extrahiert -> {out_file}")


# --------------------------------------------------------------------------------
def create_mp4_with_gpmf(video_file: str, devc_source, output_file: str) -> None:
    """Fügt einen GPMF-Track zu einem reparierten Video hinzu.
    
    :param video_file: (str) Beschreibung von video_file.
    :param devc_source: (Any) Beschreibung von devc_source.
    :param output_file: (str) Beschreibung von output_file.
    :return: (None) Beschreibung des Rückgabewerts.
    """

    # --- Minimaler moov-Track für GPMF ---
    
    # --------------------------------------------------------------------------------
    def make_box(type_bytes: bytes, payload: bytes) -> bytes:
        """Kurzbeschreibung für make_box.
        
        :param type_bytes: (bytes) Beschreibung von type_bytes.
        :param payload: (bytes) Beschreibung von payload.
        :return: (bytes) Beschreibung des Rückgabewerts.
        """

        size = 8 + len(payload)
        return size.to_bytes(4, "big") + type_bytes + payload

    # 1. DEVC-Daten einlesen
    if isinstance(devc_source, str) or isinstance(devc_source, Path):
        # einzelne Datei
        with open(devc_source, "rb") as fd:
            devc_blocks = [fd.read()]
    elif isinstance(devc_source, list):
        # Liste von Bytes
        devc_blocks = devc_source
    else:
        raise TypeError("devc_source muss Dateipfad oder Liste von Bytes sein")

    devc_data = b"".join(devc_blocks)

    # --- ftyp-Box aus Originalvideo übernehmen ---
    with open(video_file, "rb") as fd:
        ftyp_type = fd.read(24)  # Größe 24 Bytes reicht für GoPro MP4
        ftyp_data = fd.read()  # Größe 24 Bytes reicht für GoPro MP4

    # Minimal hdlr + stsz + stbl + minf + mdia + trak
    hdlr_box = make_box(b"hdlr", b"\x00"*4 + b"meta" + b"\x00"*12)
    stsz_box = make_box(b"stsz", (0).to_bytes(4, "big") + len(devc_blocks).to_bytes(4, "big") + b"\x00\x00\x00\x00"*len(devc_blocks))
    stbl_box = make_box(b"stbl", stsz_box)
    minf_box = make_box(b"minf", stbl_box)
    mdia_box = make_box(b"mdia", hdlr_box + minf_box)
    trak_box = make_box(b"trak", mdia_box)
    moov_box = make_box(b"moov", trak_box)

    # --- mdat-Box für DEVC-Daten ---
    mdat_box = make_box(b"mdat", devc_data)

    # --- finale MP4 schreiben ---
    with open(output_file, "wb") as fd:
        fd.write(ftyp_type)  # ftyp
        fd.write(moov_box)  # moov mit GPMF-Track
        fd.write(ftyp_data)  # Original Video/Audio-MDAT
        fd.write(mdat_box)  # GPMF-MDAT

    print(f"MP4 mit GPMF-Track erstellt: {output_file}")


# Beispiel mit Datei
# create_mp4_with_gpmf("1-repariert.mp4", "1-clean-rawstream.bin", "1-final-with-gpmf.mp4")
# Beispiel mit Liste von DEVC-Blöcken:
# devc_blocks = [block1_bytes, block2_bytes, block3_bytes]
# create_mp4_with_gpmf("1-repariert.mp4", devc_blocks, "1-final-with-gpmf.mp4")


# ==========================================================================
# ==========================================================================
if __name__ == "__main__":
    pathstr = "C:/Users/Ralf/Downloads/rep/"
    infile = pathstr + "1-error.mp4"
    outfile = pathstr + "1-clean.bin"
    atomfile = pathstr + "1-atom.bin"
    repfile = pathstr + "1.mp4"
    finalfile = pathstr + "1-final-with-gpmf.mp4"

    # Liste einzelner DEVC-Blöcke (bytes je Block)
    blocks = extract_devc(infile, clean=True, join=False)
    if isinstance(blocks, list):
        out_file_new = Path(outfile).with_suffix(".blocks.bin")
        with out_file_new.open("wb") as f:
            for b in blocks:
                f.write(b)

    # Ein zusammenhängender Bytestream (alle DEVC-Blöcke hintereinander)
    raw_stream = extract_devc(infile, clean=True, join=True)
    if isinstance(raw_stream, bytes):
        out_file_new = Path(outfile).with_suffix(".rawstream.bin")
        with out_file_new.open("wb") as f:
            f.write(raw_stream)

    # „Rohe“ Extraktion (keine Duplikat-Filter, nur Header-Prüfung)
    raw_blocks = extract_devc(infile, clean=False, join=False)
    if isinstance(raw_blocks, list):
        out_file_new = Path(outfile).with_suffix(".rawblocks.bin")
        with out_file_new.open("wb") as f:
            for b in raw_blocks:
                f.write(b)

        # Atom Daten erzeugen
        # make_udta_with_gpmf(Path(atomfile), raw_stream)
        create_mp4_with_gpmf(repfile, out_file_new, finalfile)

# ==========================================================================
# ==========================================================================
