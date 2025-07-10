import time
from datetime import timedelta
import tempfile, subprocess, os, heapq
from amplify import (
    VariableGenerator,
    greater_equal,
    PolyArray,
    AcceptableDegrees,
    Model,
    GurobiClient,
    FixstarsClient,
    ToshibaSQBM2Client,
    LeapHybridSamplerClient,
    DWaveSamplerClient,
    solve
)

class Hypergraph:
    """
    A hypergraph (set system) that supports to compute hitting sets (subsets of the universe that intersect all sets in the system)
    using an Ising machine in the Fixstars Amplify cloud.

    Attributes:
    n (int): The number of vertices {0...n-1}.
    edges (list of list of int): The edges (or sets) in the hypergraph (set system).
    weights (list of floats): The weights of the vertices.
    config (dictionary): The configuration of the solver.
    ipucalls (int): Accumulated number of calls to the IPU.
    encodingtime: Accumulated time to produce QUBO encodings.
    annealingtime: Accumulated time spend on the IPU.

    Methods:
    add_edge(list of int):
      Adds the given edge to the set system.
    set_weight(int, float):
      Sets the weight of a vertex
    add_to_weight(v, float):
      Adds the given weight to the current weight of a vertex.
    get_weight(int):
      Returns the weight of the given vertex.
    compute_hs(bool):
      Computes a hitting set of the graph. If the flag is set to True, a simple heuristic is used,
      otherwise the IPU is used.       
    """    
    __slots__ = 'n', 'edges', 'weights', 'config', 'ipucalls', 'encodingtime', 'annealingtime'
    
    def __init__(self, n, config):
        """
        Default constructor.

        Parameters:
        n: The number of vertices.
        config: Dictionary with the solver configuration.
        """
        self.n             = n
        self.edges         = []
        self.weights       = [0] * n
        self.config        = config
        self.ipucalls      = 0
        self.encodingtime  = 0
        self.annealingtime = 0

    def add_edge(self, e):
        """
        Add an edge to the hypergraph.

        Parameters:
        e (list of int): A list of integers representing the vertices of the edge.
        """
        self.edges.append(e)

    def set_weight(self, v, w):
        """
        Set the weight of a vertex.

        Parameters:
        v (int): The vertex whose weight is to be set.
        w (float): The weight to be assigned to the vertex.
        """
        self.weights[v] = w

    def add_to_weight(self, v, w):
        """
        Add to the current weight of a vertex.

        Parameters:
        v (int): The vertex whose weight is to be updated.
        w (float): The amount to add to the vertex's current weight.
        """
        self.weights[v] += w

    def get_weight(self, v):
        """
        Retrieve the weight of a vertex.

        Parameters:
        v (int): The vertex whose weight is to be retrieved.

        Returns:
        float: The weight of the vertex.
        """
        return self.weights[v]
    
    def compute_hs(self, heuristic = False):
        """
        Computes a hitting set of the hypergraph.
        Either with a simple heuristic, or using an IPU in Fixstars Amplify cloud.

        Parameters:
        heuristic (bool): Use a heuristic instead of the IPU (default: False).
        """
        # compute the hitting set with a heuristic
        if heuristic:
            return self._hs_simple()
        
        # end of recursion
        if len(self.edges) == 0:
            return []
        
        # compute a hitting set using the Ising machine
        self.ipucalls += 1
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
                result.append(v)
        # done
        return result

    def _hs_simple(self):
        """
        Simple heuristic to compute a hitting: Just pick the vertex that is contained
        in the most edges and remove it together with all edges it hits.
        """
        result = []
        watch = {}
        for v in range(self.n):
            watch[v] = set()
        for (i,e) in enumerate(self.edges):
            for v in e:
                watch[v].add(i)
                
        queue = []
        for v in range(self.n):
            heapq.heappush(queue, (-len(watch[v]), v))

        while len(queue) > 0:
            (deg, v) = heapq.heappop(queue)
            if -deg != len(watch[v]):
                continue
            if deg == 0:
                break
            result.append(v)
            for i in watch[v].copy():
                for w in self.edges[i]:
                    watch[w].remove(i)
                    heapq.heappush(queue, (-len(watch[w]), w))
        return result
            
    
    def _create_model(self):
        """
        Auxiliary method to create a QUBO model for the hitting set problem.

        
        This function also measures the time spent building the model.
        """
        tstart = time.time()
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

        # done
        self.encodingtime += (time.time() - tstart)
        return imodel, mapping

    def _solve_model(self, model, mapping):
        """
        Auxiliary method to solve a QUBO model using the Fixstars Amplify cloud.
        Supported are the Amplify Engine or Gurobi.

        This function also measures the time spent annealing.
        """
        tstart = time.time()
        print("c Calling the IPU ...", end = "", flush = True)
        if self.config['settings']['mode'] == "fixstars":
            result = self._solve_with_fixstars(model, mapping)
        elif self.config['settings']['mode'] == 'toshiba':
            result = self._solve_with_toshiba(model, mapping)
        elif self.config['settings']['mode'] == "dwave":
            result = self._solve_with_dwave(model, mapping)
        elif self.config['settings']['mode'] == "dwave_native":
            result = self._solve_with_dwave_native(model, mapping)
        elif self.config['settings']['mode'] == "gurobi":
            result = self._solve_with_gurobi(model, mapping)
        else:
            print("c Error: Unknown mode specified.")
            sys.exit(1)
        print(f" {(time.time()-tstart):06.2f}s.")
        self.annealingtime += (time.time() - tstart)            
        
        result = result.best.values
        return list(map(
            lambda vq: vq[0],
            filter(lambda vq: vq[0] < self.n and result[vq[1]] > 0.0001, enumerate(result))
        ))

    def _solve_with_gurobi(self, model, mapping):
        """
        Auxiliary method that solves the QUBO model using Gurobi.
        The Gurobi library path must be set in the configuration file in order to use this method.
        """
        client = GurobiClient(library_path=self.config['gurobi']['library_path'])
        client.parameters.time_limit = timedelta(seconds=self.config['settings']['annealing_time'])
        client.parameters.output_flag = 0
        return solve(model, client)

    def _solve_with_fixstars(self, model, mapping):
        """
        Auxiliary method that solves the QUBO model using the Fixstars Amplify Engine.
        The Fixstars Amplify token must be set in the configuration file in order to use this method.        
        """
        client = FixstarsClient()
        client.token = self.config['amplify']['token']
        client.parameters.timeout = timedelta(seconds=self.config['settings']['annealing_time'])
        client.parameters.num_gpus = 1
        return solve(model, client)

    def _solve_with_toshiba(self, model, mapping):
        """
        Auxiliary method that solves the QUBO model using the Toshiba SQBM+V2.
        The toshiba token must be set in the configuration file in order to use this method.        
        """
        client = ToshibaSQBM2Client()
        client.token = self.config['toshiba']['token']
        client.parameters.timeout = timedelta(seconds=self.config['settings']['annealing_time'])
        return solve(model, client)
    
    def _solve_with_dwave(self, model, mapping):
        """
        Auxiliary method that solves the QUBO model using the D-Wave Leap hybrid algorithm.
        The D-Wave token must be set in the configuration file in order to use this method.
        """
        client = LeapHybridSamplerClient()
        client.token = self.config['dwave']['token']
        client.solver = self.config['dwave']['solver']
        client.parameters.time_limit = float(self.config['settings']['annealing_time'])
        return solve(model, client)

    def _solve_with_dwave_native(self, model, mapping):
        """
        Auxiliary method that solves the QUBO model using the D-Wave Advantage System.
        The D-Wave token must be set in the configuration file in order to use this method.
        """
        client = DWaveSamplerClient()
        client.token = self.config['dwave']['token']
        client.solver = self.config['dwave']['solver']
        client.parameters.num_reads = self.config['dwave']['runs']
        return solve(model, client)

    def __str__(self):
        """
        String representation of the hypergraph.

        Returns:
        A string representing the hypergraph.
        """      
        buffer = []
        for v in range(self.n):
            buffer.append(f"c w({v}) = {self.weights[v]}")
        for e in self.edges:
            buffer.append(f"{' '.join(map(str,e))}")
        return "\n".join(buffer)
