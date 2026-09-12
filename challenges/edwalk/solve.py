#!/usr/bin/env python3
"""edwalk -- the flag is in a dead function that only the source map still has.

The deployed bundle app-DVrlaJt-.js is a purely client-side fake chatbot with
canned replies, and one of those replies is the hint:

    "Would you like some help pushing your source maps to npm?"

/assets/app-DVrlaJt-.js.map is served, and its `sourcesContent` holds the
original src/app.js -- including a getFlag() that the bundler tree-shook out
because nothing calls it.  Reimplementing it:

  * `_reverse` is reduceRight-push, i.e. the byte array reversed;
  * each byte is rotated right by 3 (`_rotateTheWrongWayFirst`);
  * the key is `((i*73 + 41) ^ ((i % 7) * 19)) & 0xff` -- the lunarPhase /
    entropy business is multiplied by `& 0`, so it contributes nothing;
  * checksumThatNobodyChecks and auditTrail are, as named, never checked.
"""
ARCHIVE = [
    120, 167, 125, 113, 225, 231, 149, 184, 255, 71, 34, 203, 140, 5, 154,
    255, 190, 192, 121, 78, 21, 146, 151, 39, 112, 81, 188, 252, 113, 215,
    247, 152, 91, 70, 221, 219, 31, 135, 208, 155, 22, 151, 107, 85, 7, 210,
    154, 20, 165, 219, 5, 239, 186, 120, 36, 173, 51, 93, 15, 176, 106, 70,
    127, 203, 149, 231, 48, 24, 54, 61, 33, 173, 39, 112, 106, 222, 117,
    179, 200, 231, 144, 10, 6, 109, 163, 192, 135, 72, 162, 124, 253, 1,
    170, 223, 120, 146, 30, 21, 155, 208, 47, 112, 34, 102, 101, 155, 232,
    71, 112, 131,
]


def rotate_right(value, distance, width=8):
    n = ((distance % width) + width) % width
    return ((value >> n) | (value << (width - n))) & 0xFF


def key_byte(offset):
    # `apparentlyImportant & 0` is zero, so only actualKey survives.
    return ((offset * 73 + 41) ^ ((offset % 7) * 19)) & 0xFF


data = ARCHIVE[::-1]
out = bytes(rotate_right(b, 3) ^ key_byte(i) for i, b in enumerate(data))
print(out.decode())
