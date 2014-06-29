""" 
Command Line Usage: 
    python -m IPython start_magic.py -i
  
Interactive Usage:
    In [1]: %run start_newtabmagic.ipy
    Starting job # 0 in a separate thread.
    Server running at http://127.0.0.1:8889/

"""
ip = get_ipython()
ip.run_cell('%load_ext newtabmagic')
ip.run_cell('%newtab --port 8889')
ip.run_cell('%newtab --browser firefox')
ip.run_cell('%newtab --file-uri-scheme view-source')
ip.run_cell('%newtab --server start')
