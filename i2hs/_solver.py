import time
from i2hs import Hypergraph, BiMap
from pysat.solvers import Solver as SATSolver

class Solver:
    """
    A (prototype) MaxSAT solver based on the implicit Ising hitting set algorithm.

    Attributes:
    phi (pysat.CNF): A propositional formula representing the constraint system.
    relaxation (list of tuple of (int, float)): Relaxation variables (i.e., soft literals) and their weight.
    hypergraph (i2hs.Hypergraph): A representation of the extracted cores.
    mapping (i2h.BiMap): Mapping between relaxation variables and hypergraph vertices.
    sattime (float): Accumulated time spend in the SAT solver.

    Methods:
    run():
      Executes the solver and returns an assignment.
    """
    __slots__ = 'phi', 'relaxation', 'hypergraph', 'mapping', 'sattime'
    
    def __init__(self, phi, relaxation, config):
        """
        Default constructor.

        Parameters:
        phi: CNF formula that represents the WCNF with relaxation variables.
        relaxation: List of relaxation variables and their weight.
        config: Dictionary with the solver configuration.
        """
        self.phi        = phi
        self.relaxation = relaxation
        self.hypergraph = Hypergraph(len(relaxation), config)
        self.mapping    = BiMap()
        self.sattime    = 0
        for (i,(v,weight)) in enumerate(relaxation):
            self.mapping.insert(v,i)
            self.hypergraph.set_weight(i, weight)

    def _run_satsolver(self, satsolver, assumption):
        """
        Auxiliary method to run the SAT solver under the given assumption and measure the time.

        Parameters:
        satsolver: The PySAT SAT solver.
        assumptions: List of literals to be assumed.
        """
        tstart        = time.time()
        satresult     = satsolver.solve( assumptions = assumption )
        self.sattime += (time.time() - tstart)
        return satresult

    def _extract_core(self, satsolver):
        core = satsolver.get_core()
        if core is None:
            False
        self.hypergraph.add_edge(
            list(map(lambda v:self.mapping.get_value(v), core))
        )
        return True

        
    def run(self):
        """
        Executes the implicit Ising hitting set algorithm to find a solution for the MaxSAT instance.
        """
        relaxation_vars = set(map(lambda v: v[0], self.relaxation))
        satsolver = SATSolver(name='g3', bootstrap_with = self.phi.clauses )
        
        while True:
            # The outer loop computes hitting sets with a heuristic.
            hittingset = set( map(lambda v: self.mapping.get_key(v), self.hypergraph.compute_hs(heuristic=True)) )
            assumption = relaxation_vars.difference(hittingset)
            if self._run_satsolver(satsolver, assumption):
                # If the formula is satisfiable under the assumption computed with the heuristic,
                # we compute hitting sets with the IPU.
                hittingset = set( map(lambda v: self.mapping.get_key(v), self.hypergraph.compute_hs()) )
                assumption = relaxation_vars.difference(hittingset)                
                if self._run_satsolver(satsolver, assumption):
                    # The formula is also satisfiable under the assumptions computed with the IPU.
                    # This is the best solution we can hope for and, hence, we terminate.
                    # Note that we do *not* have necessarily reached an optimum unless we use an exact IPU.
                    break
                elif not self._extract_core(satsolver):
                    break                                                
            elif not self._extract_core(satsolver):
                break

        # Map the model back to the original problem.
        model = satsolver.get_model()
        if model:
            assignment = model[:len(model)-len(relaxation_vars)]
            cost = sum(map(
                    lambda v: self.hypergraph.get_weight(self.mapping.get_value(v)),
                    filter(lambda v: v not in model, relaxation_vars)
                ))
            fitness = sum(map(
                lambda v: self.hypergraph.get_weight(self.mapping.get_value(v)),
                relaxation_vars
            )) - cost
            return assignment, cost, fitness
        return None
                

