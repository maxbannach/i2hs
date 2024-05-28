import time
from i2hs import Hypergraph, BiMap
from pysat.solvers import Solver as SATSolver


class Solver:
    __slots__ = 'phi', 'relaxation', 'hypergraph', 'mapping', 'sattime'
    
    def __init__(self, phi, relaxation, config):
        self.phi        = phi
        self.relaxation = relaxation
        self.hypergraph = Hypergraph(len(relaxation), config)
        self.mapping    = BiMap()
        self.sattime    = 0
        for (i,(v,weight)) in enumerate(relaxation):
            self.mapping.insert(v,i)
            self.hypergraph.set_weight(i, weight)

    def _run_satsolver(self, satsolver, assumption):
        tstart        = time.time()
        satresult     = satsolver.solve( assumptions = assumption )
        self.sattime += (time.time() - tstart)
        return satresult

            
    def run(self):
        relaxation_vars = set(map(lambda v: v[0], self.relaxation))
        satsolver = SATSolver(name='g3', bootstrap_with = self.phi.clauses )
        
        while True:
            hittingset = set( map(lambda v: self.mapping.get_key(v), self.hypergraph.compute_hs(heuristic=True)) )
            assumption = relaxation_vars.difference(hittingset)
            if self._run_satsolver(satsolver, assumption):
                hittingset = set( map(lambda v: self.mapping.get_key(v), self.hypergraph.compute_hs()) )
                assumption = relaxation_vars.difference(hittingset)                
                if self._run_satsolver(satsolver, assumption):
                    break
                else:
                    core = satsolver.get_core()
                    if core is None:
                        break
                    self.hypergraph.add_edge(
                        list(map(lambda v:self.mapping.get_value(v), core))
                    )
                                                
            else:            
                core = satsolver.get_core()
                if core is None:
                    break
                self.hypergraph.add_edge(
                    list(map(lambda v:self.mapping.get_value(v), core))
                )
                
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
                

