import logging


def configure_logger(logger):
    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    handler.setLevel(logging.DEBUG)

    # add ch to logger
    logger.addHandler(handler)


logger = logging.getLogger(__name__)

configure_logger(logger)
