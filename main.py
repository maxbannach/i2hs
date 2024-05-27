import sys, time, yaml, argparse
from pysat.formula import CNF
from i2hs import Hypergraph, Solver

__version__ = "1.0.0"
__author__  = "Max Bannach"

def section(s):
    print(f"c ---- [ {s} ] ----", end="")
    remaining = 80 - 16 - len(s)
    for _ in range(remaining):
        print("-", end="")
    print("\nc")

def arguments():
    parser = argparse.ArgumentParser(
        description='A simple MaxSAT solver based on Implicit Ising Hitting Set.'
    )
    parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(__version__))
    parser.add_argument("-f", "--file", type=argparse.FileType("r"), default=sys.stdin, help="Input formula (as DIMACS2022 wcnf). Default is stdin.")
    parser.add_argument("-c", "--config", type=str, default="config.yaml", help="Path to the configuration file. Default is config.yaml.")
    return parser.parse_args()
            
def load_config(path):
    with open(path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == "__main__":
    section("Implicit Ising Hitting Set")
    print(f"c Version: {__version__}")
    print(f"c Authors: {__author__}\nc")

    # Load arguments and configuration.
    args   = arguments()
    config = load_config(args.config)
    print(f"c Gurobi Library: {config['gurobi']['library_path']}")
    print(f"c Amplify Token:  {config['amplify']['token']}")
    print("c")
    
    section("Parsing Input")
    tstart = time.time()    
    print(f"c Parsing the input formula ...", end = "", flush=True)
    phi    = CNF()
    free = 0; relaxation = []; buffer = [] 
    for line in args.file:
        line = line.strip()
        if line.startswith(('c', 'p')):
            continue # Skip comments and problem lines.

        # Weight and clause. Update free next free variable.
        w, c = line.split(" ")[0], [int(x) for x in line.split(" ")[1:-1]]
        free = max(free, max(map(lambda l: abs(l), c)))

        # Hard clauses can be added directly, soft clauses
        # are added later using relaxation variables.
        if w == 'h':
            phi.append(c)
        else:
            assert( float(w) >= 0 )
            buffer.append( (float(w),c) )

    # Add the soft clauses using relaxation variables.
    for (w,c) in buffer:
        free += 1; c.append(-free)
        phi.append(c)
        relaxation.append( (free,w) )
    print(f" {(time.time()-tstart):06.2f}s.\nc")

    section("Invoking Ising Machine")
    tstart = time.time()    
    solver = Solver(phi, relaxation, config)
    result = solver.run()

    # Output the result.
    if result is None:
        print(f"s UNSATISFIABLE")
    else:
        assignment, cost, fitness = result
        print(f"c Fitness:    {fitness}")
        print(f"c Cost:       {cost}")
        print("c")
        print(f"s SATISFIABLE")
        print(f"o {cost}")
        for (i,l) in enumerate( assignment ):
            if i % 25 == 0:
                if i > 0:
                    print()
                print("v", end="")
            print(f" {l}", end="")
        print("\nc")
        
    
    print(f"c Solved in {(time.time()-tstart):06.2f}s.\nc")

    
