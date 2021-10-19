import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
fmt = logging.Formatter("%(asctime)s -- %(levelname)s: %(message)s")
handler.setFormatter(fmt)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

