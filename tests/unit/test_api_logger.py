import logging
import tempfile
from pathlib import Path
from api import logger as api_logger


def test_enregistrer_photo_suppression_logs_message():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        log_path = f.name

    root_logger = logging.getLogger()
    handler = logging.FileHandler(log_path, encoding='utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    try:
        api_logger.enregistrer_photo_suppression('/photos/photo_to_delete.jpg')
        handler.flush()
    finally:
        root_logger.removeHandler(handler)
        handler.close()

    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    assert any('[CAMERA] Photo supprimée : /photos/photo_to_delete.jpg' in line for line in lines)

    Path(log_path).unlink(missing_ok=True)
