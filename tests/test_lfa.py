"""lfa runs the book's .elpi files on the leanelpi wheel
and prints what lean-elpi prints. tests/run_elpi.py --lfa
checks every golden file; these are the parts it relies on."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def lfa(*args, cwd="ch01", stdin=None):
    p = subprocess.run([sys.executable, str(ROOT / "lfa.py"),
                        *args, "-I", "../lib"],
                       cwd=ROOT / cwd, input=stdin,
                       capture_output=True, text=True,
                       timeout=120)
    return p.returncode, p.stdout, p.stderr


def test_test_runs_main():
    rc, out, _ = lfa("phantom.elpi", "-test")
    assert (rc, out) == (0, "anna in berlin and lisbon\n")


def test_repl_prints_in_query_order():
    rc, out, _ = lfa("phantom.elpi", stdin="works_at P Acme.\nn\n")
    assert rc == 0
    assert out.index("P = anna") < out.index("Acme = acme")


def test_errors_point_into_the_original_file():
    rc, _, err = lfa("bad_rule.elpi", "-test", cwd="ch04")
    assert rc == 1
    assert err.startswith("bad_rule.elpi:7:44:")


def test_lf_files_need_lean_elpi():
    rc, _, err = lfa("plain.elpi", "-test", cwd="ch10")
    assert rc == 1 and "needs the lean-elpi program" in err


def test_load_gives_a_program():
    sys.path.insert(0, str(ROOT))
    from lfa import load
    p = load(ROOT / "ch01" / "phantom.elpi")
    assert [s["P"] for s in p.solve("works_at P acme")] == \
        ["anna", "marco"]
