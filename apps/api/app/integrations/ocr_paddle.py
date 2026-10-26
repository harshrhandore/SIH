"""Optional adapter for an owner-provisioned PaddleOCR engine.

The unattended build never installs Paddle or downloads models (prompt0.7).
An explicit engine instance is required; absence never pretends OCR succeeded.
"""

import numpy as np


def extract(image, engine):
    if engine is None:
        return "", ["PaddleOCR is not provisioned; this engine was not assessed."]
    try:
        pages = engine.ocr(np.asarray(image.convert("RGB")), cls=True)
        text = "\n".join(str(line[1][0]) for page in (pages or []) for line in (page or []))
        return text[:16000], []
    except (ValueError, TypeError, RuntimeError):
        return "", ["PaddleOCR did not produce readable text."]
