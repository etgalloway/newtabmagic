ip = get_ipython()
ip.run_cell('%load_ext newtabmagic')
ip.run_cell('%newtab --port 8889')
ip.run_cell('%newtab --browser firefox')
ip.run_cell('%newtab --server start')
