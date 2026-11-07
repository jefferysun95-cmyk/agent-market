"""Shared test setup, never used by the production server."""
import unittest
from tests import test_market as legacy
from server import Problem

class Base(unittest.TestCase):
    # Share fixtures without rediscovering or inheriting the original tests.
    setUp = legacy.MarketTest.setUp
    tearDown = legacy.MarketTest.tearDown
    register = legacy.MarketTest.register
    call = legacy.MarketTest.call
    fail = legacy.MarketTest.fail
    select = legacy.MarketTest.select
