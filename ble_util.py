#!/usr/bin/env python3

from logging import getLogger, basicConfig
import logging

LOG_LEVEL = logging.INFO

format = "%(asctime)s [%(levelname)7s] %(pathname)s(%(lineno)s)\tfn:%(funcName)30s(): %(message)s"

basicConfig(format=format, level=LOG_LEVEL)
LOG = getLogger(__name__)
