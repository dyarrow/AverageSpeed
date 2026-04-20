"""
Neology Average Speed — Regression Test Runner
================================================
Runs the comparison engine against known-good test files and
checks results match the expected CSV exactly.

Each test supports one or more VRM groups — same as the wizard.
Results from all groups are accumulated and compared against
a single expected CSV.

Usage:
    python test_runner.py
    python test_runner.py --verbose     # show full row diffs
    python test_runner.py --update      # overwrite expected CSV with current output
    python test_runner.py --test ANZ    # run only tests whose name contains 'ANZ'
"""

import os, sys, csv, argparse, types

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))   # .../Testing/
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)                  # .../AverageSpeed/
TEST_DATA   = os.path.join(SCRIPT_DIR, "test_data")

# ── Mock PyQt5 and reportlab for headless running ─────────────────────────────
def _setup_mocks():
    if 'PyQt5' not in sys.modules:
        qt     = types.ModuleType('PyQt5')
        qtcore = types.ModuleType('PyQt5.QtCore')
        class _QThread: pass
        class _Signal:
            def __init__(self, *a): pass
            def emit(self, *a): pass
            def connect(self, *a): pass
        qtcore.QThread     = _QThread
        qtcore.pyqtSignal  = lambda *a: _Signal()
        qt.QtCore          = qtcore
        sys.modules['PyQt5']        = qt
        sys.modules['PyQt5.QtCore'] = qtcore

    try:
        import reportlab  # noqa
    except ImportError:
        for mod in [
            'reportlab', 'reportlab.lib', 'reportlab.lib.pagesizes',
            'reportlab.lib.colors', 'reportlab.platypus', 'reportlab.lib.styles',
            'reportlab.lib.units', 'reportlab.pdfbase', 'reportlab.pdfbase.pdfmetrics',
            'reportlab.pdfbase.ttfonts',
        ]:
            sys.modules.setdefault(mod, types.ModuleType(mod))

    if 'build_config' not in sys.modules:
        bc                 = types.ModuleType('build_config')
        bc.resourcesPath   = PROJECT_DIR
        bc.applicationPath = PROJECT_DIR
        sys.modules['build_config'] = bc

_setup_mocks()
sys.path.insert(0, PROJECT_DIR)

# ── Test definitions ───────────────────────────────────────────────────────────
# Each test has:
#   name       — human-readable label
#   obo        — path to OBO xlsx file (shared across all VRM groups)
#   vrm_groups — list of {plate, plate_hash, vbo_files} dicts
#                single-VRM tests just have one entry in the list
#   expected   — path to expected results CSV

TESTS = [
    {
        "name": "ANZ6427 Day 5 — single VRM",
        "obo":  os.path.join(TEST_DATA, "wsdot_day5_ANZ6427_obo_data.xlsx"),
        "vrm_groups": [
            {
                "plate":      "ANZ6427",
                "plate_hash": "",
                "vbo_files":  [os.path.join(TEST_DATA, "wsdot_day5_ANZ6427_gps_data.vbo")],
            },
        ],
        "expected": os.path.join(TEST_DATA, "wsdot_day5_ANZ6427_test_results.csv"),
    },
    # Multi-VRM example:
    {
        "name": "Multi VRM Day 6",
         "obo":  os.path.join(TEST_DATA, "wsdot_day6_multivrm_obo_data.xlsx"),
         "vrm_groups": [
             {"plate": "ANZ6427", "plate_hash": "", "vbo_files": [os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(1).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(2).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(3).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(4).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(5).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(6).vbo"),
                                                                os.path.join(TEST_DATA, "wsdot_day6_multivrm_Charger(7).vbo")]},
             {"plate": "922GKV", "plate_hash": "", "vbo_files": [os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(1).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(2).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(3).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(4).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(5).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(6).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(7).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(8).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(9).vbo")]},
             {"plate": "345287", "plate_hash": "", "vbo_files": [os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(1).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(2).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(3).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(4).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(5).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(6).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(7).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(8).vbo"),
                                                                 os.path.join(TEST_DATA, "wsdot_day6_multivrm_BMW(9).vbo")]},
         ],
         "expected": os.path.join(TEST_DATA, "wsdot_day6_multivrm_test_results.csv"),
    },
]

# ── Config (must match your neology_average_speed.json) ───────────────────────
CONFIG = {
    "AverageSpeed": {
        "time_offset":        "0",
        "leap_seconds":       "0",
        "min_sats":           "4",
        "threshold_low_pos":  "3",
        "threshold_low_neg":  "3",
        "threshold_high_pos": "3",
        "threshold_high_neg": "3",
        "speed_breakpoint":   "62",
        "pct_only":           "false",
        "validation_enabled": "true",
    }
}

HEADERS = [
    'Passage', 'Pri Entry Time', 'Sec Entry Time', 'Entry Time Diff',
    'Pri Exit Time', 'Sec Exit Time', 'Exit Time Diff', 'VRM', 'From', 'To',
    'Vbox Average Spd', 'Pri OBO Spd', 'Vbox/Pri Speed % Diff',
    'Vbox / Pri Speed MPH Diff', 'Sec OBO Speed', '% Pri/Sec Spd Diff',
    'FromVboxCutTime', 'ToVboxCutTime', 'GPS Points', '# Errors (low satellite)'
]

EXACT_COLS = ["Passage", "VRM", "From", "To", "GPS Points", "# Errors (low satellite)"]
FLOAT_COLS = {
    "Vbox Average Spd":          0.01,
    "Pri OBO Spd":               0.001,
    "Vbox/Pri Speed % Diff":     0.01,
    "Vbox / Pri Speed MPH Diff": 0.01,
    "Sec OBO Speed":             0.001,
    "% Pri/Sec Spd Diff":        0.01,
    "Entry Time Diff":           0.01,
    "Exit Time Diff":            0.01,
}
SKIP_COLS = ["FromVboxCutTime", "ToVboxCutTime"]  # GPS cut times can vary by 1 point


# ── Headless UI stub ───────────────────────────────────────────────────────────
class _FakeUI:
    pbTotal    = 10
    pbProgress = 0
    class updateAverageSpeedValidationPB:
        @staticmethod
        def emit(d):
            msg = d.get('message', '')
            pct = d.get('progress', 0)
            if msg:
                print(f"    [{pct:>3}%] {msg:<50}", end='\r')


# ── Run one test ───────────────────────────────────────────────────────────────
def run_test(test, verbose=False, update=False):
    from link_validation import linkValidation, linkValidationData

    print(f"\n{'='*60}")
    print(f"  TEST: {test['name']}")
    print(f"{'='*60}")
    print(f"  OBO : {os.path.basename(test['obo'])}")

    groups    = test["vrm_groups"]
    obo_files = [test["obo"]]
    all_rows  = []

    for i, grp in enumerate(groups):
        plate      = grp.get("plate", "")
        plate_hash = grp.get("plate_hash", "")
        vbo_files  = grp.get("vbo_files", [])
        label      = plate or plate_hash or f"group {i+1}"

        print(f"  VRM  [{i+1}/{len(groups)}]: {label}")
        for vbo in vbo_files:
            print(f"    VBO: {os.path.basename(vbo)}")

        val_data                     = linkValidationData()
        val_data.gpsFilenames        = vbo_files
        val_data.ercuFilenames       = obo_files
        val_data.commissioningConfig = CONFIG

        ui         = _FakeUI()
        ui.pbTotal = len(vbo_files) + len(obo_files) + 1

        lv = linkValidation(ui)
        try:
            result = lv.manualComparison(val_data, plate, plate_hash)
        except Exception as e:
            print(f"\n  ✖ COMPARISON FAILED for {label}: {e}")
            return False

        if result is None:
            print(f"\n  ✖ NO RESULT for {label} — check plate/OBO match")
            return False

        print(f"\n    → {len(result.validationResultData)} passages found")
        all_rows.extend(result.validationResultData)

    # ── Update mode ───────────────────────────────────────────────────────────
    if update:
        with open(test["expected"], "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            for row in all_rows:
                writer.writerow(row)
        print(f"\n  ✔ UPDATED expected CSV ({len(all_rows)} rows) → {test['expected']}")
        return True

    # ── Load expected ─────────────────────────────────────────────────────────
    if not os.path.exists(test["expected"]):
        print(f"\n  ✖ EXPECTED FILE NOT FOUND: {test['expected']}")
        print(f"    Run with --update to create it")
        return False

    with open(test["expected"], newline="") as f:
        expected_rows = list(csv.DictReader(f))

    actual_rows = [dict(zip(HEADERS, r)) for r in all_rows]

    # ── Check 1: passage count ────────────────────────────────────────────────
    print(f"\n  Passages — expected: {len(expected_rows)}  actual: {len(actual_rows)}", end="  ")
    if len(actual_rows) != len(expected_rows):
        print("✖ FAIL")
        exp_ids = {r["Passage"] for r in expected_rows}
        act_ids = {r["Passage"] for r in actual_rows}
        missing = exp_ids - act_ids
        extra   = act_ids - exp_ids
        if missing: print(f"    Missing : {sorted(missing)}")
        if extra:   print(f"    Extra   : {sorted(extra)}")
        return False
    print("✔ PASS")

    # ── Check 2: row-by-row diff ──────────────────────────────────────────────
    errors = []
    for i, (exp, act) in enumerate(zip(expected_rows, actual_rows)):
        row_errors = []
        for col in HEADERS:
            if col in SKIP_COLS:
                continue
            e_val = str(exp.get(col, "")).strip()
            a_val = str(act.get(col, "")).strip()
            if col in EXACT_COLS:
                if e_val != a_val:
                    row_errors.append(f"{col}: expected '{e_val}' got '{a_val}'")
            elif col in FLOAT_COLS:
                try:
                    tol  = FLOAT_COLS[col]
                    diff = abs(float(e_val) - float(a_val))
                    if diff > tol:
                        row_errors.append(
                            f"{col}: expected {e_val} got {a_val} "
                            f"(diff={diff:.4f}, tol={tol})"
                        )
                except ValueError:
                    if e_val != a_val:
                        row_errors.append(f"{col}: expected '{e_val}' got '{a_val}'")
        if row_errors:
            errors.append((exp.get("Passage", f"row {i+1}"), row_errors))

    if errors:
        shown = errors if verbose else errors[:3]
        print(f"\n  Row diffs — {len(errors)} passage(s) with differences:")
        for passage_id, errs in shown:
            print(f"\n    Passage {passage_id}:")
            for e in errs:
                print(f"      • {e}")
        if not verbose and len(errors) > 3:
            print(f"\n    ... {len(errors)-3} more — run with --verbose to see all")
        print(f"\n  ✖ FAIL — {len(errors)}/{len(actual_rows)} passages differ")
        return False

    print(f"  Row diff   — all {len(actual_rows)} passages match  ✔ PASS")
    print(f"\n  ✔ ALL CHECKS PASSED")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Neology Average Speed regression tests")
    parser.add_argument("--verbose", action="store_true", help="Show all row diffs")
    parser.add_argument("--update",  action="store_true", help="Overwrite expected CSVs with current output")
    parser.add_argument("--test",    type=str, default=None, help="Run only tests whose name contains this string")
    args = parser.parse_args()

    tests = TESTS
    if args.test:
        tests = [t for t in TESTS if args.test.lower() in t["name"].lower()]
        if not tests:
            print(f"No tests matching '{args.test}'")
            sys.exit(1)

    passed = failed = 0
    for test in tests:
        ok = run_test(test, verbose=args.verbose, update=args.update)
        if ok: passed += 1
        else:  failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed  ({len(tests)} total)")
    print(f"{'='*60}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()