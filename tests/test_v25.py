"""V2.5: layer count chosen automatically or by the user; inner planes on 4/6 layers."""

import unittest
from types import SimpleNamespace as NS

from kipcb import sizemodel, stackup


class _Fp:
    def __init__(self, pads, pitch):
        self.pads, self._pitch = [None] * pads, pitch

    def pitch(self):
        return self._pitch


def _part(ref, value, fp_id="Package_SO:SOIC-8", pads=8, pitch=1.27):
    return NS(ref=ref, value=value, symbol_id="x:" + value, footprint_id=fp_id, fp=_Fp(pads, pitch))


def _design(layers=4, parts=(), planes=None, power=("GND", "+3V3", "VBUS")):
    board = {"layers": layers}
    if planes is not None:
        board["planes"] = planes
    nets = {"GND": list(range(12)), "+3V3": list(range(8)), "VBUS": list(range(3)), "SDA": [1, 2]}
    return NS(board=board, nets=nets, power_nets=list(power), components=list(parts))


class PlanTests(unittest.TestCase):
    def test_two_layers_have_no_planes(self):
        self.assertEqual(stackup.plan(_design(2)), {})

    def test_four_layers_gnd_then_busiest_rail(self):
        self.assertEqual(stackup.plan(_design(4)), {"In1.Cu": "GND", "In2.Cu": "+3V3"})

    def test_six_layers_keep_middle_layers_for_signals(self):
        self.assertEqual(stackup.plan(_design(6)), {"In1.Cu": "GND", "In4.Cu": "+3V3"})

    def test_planes_override_and_empty_means_none(self):
        self.assertEqual(stackup.plan(_design(4, planes={"In2.Cu": "VBUS"})), {"In2.Cu": "VBUS"})
        self.assertEqual(stackup.plan(_design(4, planes={})), {})

    def test_check_rejects_outer_layers_unknown_nets_and_2_layers(self):
        self.assertTrue(stackup.check(_design(4, planes={"F.Cu": "GND"})))
        self.assertTrue(stackup.check(_design(4, planes={"In1.Cu": "NOPE"})))
        self.assertTrue(stackup.check(_design(2, planes={"In1.Cu": "GND"})))
        self.assertEqual(stackup.check(_design(4, planes={"In1.Cu": "GND"})), [])


class ChooseTests(unittest.TestCase):
    def setUp(self):
        self._features, self._vote = sizemodel.features, sizemodel.layer_vote
        sizemodel.features = lambda d: {"conns": 40}
        self.vote = (0.1, 30)
        sizemodel.layer_vote = lambda f, rows=None: self.vote

    def tearDown(self):
        sizemodel.features, sizemodel.layer_vote = self._features, self._vote

    def test_simple_board_stays_on_two(self):
        n, why = stackup.choose(_design(parts=[_part("U1", "ATtiny85")]))
        self.assertEqual(n, 2)
        self.assertIn("3 of the 30", why[0])

    def test_bga_and_high_speed_go_to_four(self):
        self.assertEqual(stackup.choose(_design(parts=[_part("U1", "X", "Package_BGA:BGA-64")]))[0], 4)
        self.assertEqual(stackup.choose(_design(parts=[_part("U2", "LAN8720A")]))[0], 4)

    def test_fine_pitch_qfn_alone_stays_on_two(self):
        # RP2040-class chips route more reliably on 2 layers today
        self.vote = (14 / 30.0, 30)
        n, _ = stackup.choose(_design(parts=[_part("U3", "RP2040", "Package_DFN_QFN:QFN-56", 57, 0.4)]))
        self.assertEqual(n, 2)

    def test_clear_majority_of_similar_boards_goes_to_four(self):
        self.vote = (0.7, 30)
        n, why = stackup.choose(_design(parts=[_part("U1", "STM32")]))
        self.assertEqual(n, 4)
        self.assertIn("21 of the 30", why[0])

    def test_without_knowledge_base_uses_connection_count(self):
        self.vote = (None, 0)
        self.assertEqual(stackup.choose(_design())[0], 2)
        sizemodel.features = lambda d: {"conns": 200}
        self.assertEqual(stackup.choose(_design())[0], 4)


class LayerVoteTests(unittest.TestCase):
    def test_share_of_neighbours_on_four_layers(self):
        rows = [{"layers": 4 if i % 4 == 0 else 2, "pads": 50, "parts": 20, "conns": 30,
                 "court_area": 300.0, "fine": 0.0, "board_area": 1500.0} for i in range(60)]
        share, n = sizemodel.layer_vote(rows[0], rows=rows)
        self.assertEqual(n, sizemodel.K)
        self.assertTrue(0.0 < share < 0.5)
        self.assertEqual(sizemodel.layer_vote(rows[0], rows=[]), (None, 0))


class GrowFallbackTests(unittest.TestCase):
    def test_snapshot_restore_puts_the_previous_board_back(self):
        import os, tempfile
        from kipcb import run
        d = tempfile.mkdtemp()
        p = os.path.join(d, "proj")
        os.makedirs(os.path.join(p, "reports"))
        open(os.path.join(p, "b.kicad_pcb"), "w").write("small")
        snap = run._snapshot(p)
        open(os.path.join(p, "b.kicad_pcb"), "w").write("bigger")
        open(os.path.join(p, "reports", "x.json"), "w").write("{}")
        run._restore(snap, p)
        self.assertEqual(open(os.path.join(p, "b.kicad_pcb")).read(), "small")
        self.assertFalse(os.path.exists(os.path.join(p, "reports", "x.json")))
        self.assertFalse(os.path.exists(snap))


if __name__ == "__main__":
    unittest.main()
