"""V2.7: cost estimate (bare boards, assembly, parts)."""

import unittest

from kipcb import cost

MODEL = {"pcb": {"promo": [{"layers": 2, "max_w": 100, "max_h": 100, "qty": 5, "price": 2.0},
                           {"layers": 2, "max_w": 100, "max_h": 100, "qty": 10, "price": 5.0}],
                 "per_m2": {"2": 25.0, "4": 70.6, "6": 120.0}, "minimum": {"2": 2.0, "4": 7.5, "6": 25.0}},
         "assembly": {"setup": 8.0, "per_joint": 0.0017, "extended_part_fee": 3.0}, "as_of": "test"}


class PcbPriceTests(unittest.TestCase):
    def test_small_two_layer_boards_use_the_promo_tiers(self):
        self.assertEqual(cost.pcb_price(56, 41, 2, 5, MODEL), 2.0)
        self.assertEqual(cost.pcb_price(56, 41, 2, 10, MODEL), 5.0)

    def test_big_or_many_boards_are_priced_by_area_with_a_floor(self):
        self.assertEqual(cost.pcb_price(150, 100, 2, 5, MODEL), 2.0)          # 0.075 m2 x $25 < floor
        self.assertAlmostEqual(cost.pcb_price(100, 100, 2, 100, MODEL), 25.0)  # 1 m2
        self.assertEqual(cost.pcb_price(60, 42, 4, 5, MODEL), 7.5)            # 4 layers: floor


class EstimateTests(unittest.TestCase):
    def test_totals_add_up_and_extended_parts_are_charged_once(self):
        lines = [{"refs": ["U1"], "qty": 1, "lcsc": "C1", "price": 3.0, "class": "extended"},
                 {"refs": ["C1", "C2"], "qty": 2, "lcsc": "C2", "price": 0.01, "class": "basic"},
                 {"refs": ["J1"], "qty": 1, "lcsc": "", "price": None, "class": None}]
        est = cost.estimate(56, 41, 2, lines, joints=40, quantities=(5,), model=MODEL)
        r = est["rows"][0]
        self.assertEqual(r["parts"], round(5 * (3.0 + 0.02), 2))
        self.assertEqual(r["assembly"], round(8.0 + 0.0017 * 40 * 5 + 3.0, 2))
        self.assertEqual(r["total"], round(r["pcb"] + r["assembly"] + r["parts"], 2))
        self.assertEqual(est["extended"], ["C1"])
        self.assertEqual(est["unpriced"], ["J1"])
        self.assertEqual(est["drivers"][0]["refs"], ["U1"])


if __name__ == "__main__":
    unittest.main()
