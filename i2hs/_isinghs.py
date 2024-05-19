from datetime import timedelta
from amplify import (
    VariableGenerator,
    greater_equal,
    PolyArray,
    AcceptableDegrees,
    Model,
    GurobiClient,
    FixstarsClient,
    solve
)

class Hypergraph:
    __slots__ = 'n', 'edges', 'weights', 'config'
    
    def __init__(self, n, config):
        self.n       = n
        self.edges   = []
        self.weights = [0] * n
        self.config  = config

    def add_edge(self, e):
        self.edges.append(e)

    def set_weight(self, v, w):
        self.weights[v] = w

    def add_to_weight(self, v, w):
        self.weights[v] += w

    def get_weight(self, v):
        return self.weights[v]
        
    def compute_hs(self):
        # end of recursion
        if len(self.edges) == 0:
            return []
        
        # compute a hitting set using the Ising machine
        model, mapping = self._create_model()
        result = self._solve_model(model, mapping)

        # ensure to select at least one vertex
        if len(result) == 0:
            result.append( self.edges[0][0] )
        
        # repair it if necessary
        unhit = []
        for e in self.edges:
            if not any(v in e for v in result):
                unhit.append(e)
        if len(unhit) > 0:
            h = Hypergraph(self.n, self.config)
            for e in unhit:
                h.add_edge(e)
            for v in h.compute_hs():
                result.add(v)

        # done
        return result
        
    def _create_model(self):
        rho = sum(map(lambda x: abs(x), self.weights)) + 1

        # objective: minimize the sum of weigts of selected variables
        gen = VariableGenerator()
        q   = gen.array("Binary", self.n)
        obj = self.weights * q

        # at least one constraint for every edge
        constraints = None
        for e in self.edges:            
            c = greater_equal(PolyArray(list(map(lambda v: q[v], e))).sum(), 1)
            c.weight = rho
            if constraints is None:
                constraints = c
            else:
                constraints += c

        # build a model with the objective and the constraints
        model = Model(obj.sum())
        if constraints is not None:
            model.constraints = constraints

        # transform it into an unconstrainted problem
        bq = AcceptableDegrees(objective={"Binary": "Quadratic"})
        imodel, mapping = model.to_intermediate_model(bq)
        return imodel, mapping

    def _solve_model(self, model, mapping):
        #client = GurobiClient(library_path=self.config['gurobi']['library_path'])
        #client.parameters.time_limit = timedelta(seconds=self.config['settings']['annealing_time'])

        client = FixstarsClient()
        client.token = self.config['amplify']['token']
        client.parameters.timeout = timedelta(seconds=self.config['settings']['annealing_time'])
        client.parameters.num_gpus = 1

        
        result = solve(model, client)
        return list(map(
            lambda vq: vq[0],
            filter(lambda vq: vq[0] < self.n and result.best.values[vq[1]] > 0.0001, enumerate(result.best.values))
        ))

    def __str__(self):
        buffer = []
        for v in range(self.n):
            buffer.append(f"c w({v}) = {self.weights[v]}")
        for e in self.edges:
            buffer.append(f"{' '.join(map(str,e))}")
        return "\n".join(buffer)
