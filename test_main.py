from unittest import TestCase

from main import splitOnCapital


class Test(TestCase):
    def test_split_on_capital(self):
        ans = splitOnCapital("HiI'm a stringBrr")
        do_nothing = splitOnCapital("totallynormal")
        self.assertEqual("Hi I'm a string Brr", ans)
        self.assertEqual("totallynormal", do_nothing)
