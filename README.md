# I2HS
A prototype MaxSAT solver based on the *Implicit Ising Hitting Set*
algorithm ($I^2HS$). It implements a traditional implicit hitting
algorithm for MaxSAT in which the SAT-part is handled using PySAT and
the hitting set is solved using an Ising machine in the Fixstars Amplify cloud.

# Installation

This library is based on the Fixstars Amplify cloud for Ising
machines and PySAT for satisfiability. The following dependencies must
be installed:
- amplify[extra]
- python-sat[pblib]
- pyyaml

All dependencies can be installed via pip:
```
pip install -r requirements.txt
```

# Configuration

To run the solver, the configurations in `config.yaml` must be set
first:
- If Gurobi is used as virtual Ising machine, the path to the Gurobi
  library must be set (Gurobi together with a valid license must be
  installed on the machine).
- If an Ising machine in the Fixstars Amplify cloud is used, the
  amplify token must be specified.
  
The *settings* section contains general settings:
- annealing_time: The time the Ising machine has per call to solve an hitting
  set instance (in seconds).
