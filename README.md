# leveraged_investing
Simulations of leveraged investing vs. non-leveraged. For further explanation, see http://reducing-suffering.org/why-and-how-to-leverage-investments/

To dp margin-investing simulations, run "margin_leverage.py" You can edit the section at the bottom to choose how to run different variations. Note that if you set use_multiprocessing=True, the program will use 100% of your CPU and make other applications slower because I haven't yet figured out a cross-platform way to reduce the priority of the processes that get created.

To do leveraged-ETF simulations, run "simulate_leveraged_etf.py"
