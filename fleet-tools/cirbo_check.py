"""Cirbo self-check (run by `make cirbo`): in pequalnp's model (AND, OR, NOT, NOT counted) maj3 needs exactly 4 gates."""
from cirbo.core.truth_table import TruthTable
from cirbo.synthesis.circuit_search import CircuitFinderSat, Operation
from cirbo.synthesis.exception import NoSolutionError

BASIS = [Operation.lnot_, Operation.and_, Operation.or_]
maj3 = TruthTable([[int(f"{j:03b}".count("1") >= 2) for j in range(8)]])  # row j = binary of j, input 0 = top bit
CircuitFinderSat(maj3, 4, basis=BASIS).find_circuit(time_limit=60)
try:
    CircuitFinderSat(maj3, 3, basis=BASIS).find_circuit(time_limit=60)
    raise SystemExit("cirbo check FAILED: maj3 found with 3 gates")
except NoSolutionError:
    print("cirbo ok: maj3 needs 4 AND/OR/NOT gates")
