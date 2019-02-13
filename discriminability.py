""" 
Discriminability code. Takes in output of ndmg participant-level analysis.
Currently in the root directory for safekeeping, will be moved to a better home once it's done
"""

# TODO: write test for get_graph_files
# TODO: write test for numpy_from_output_graph
# TODO: write test for matrix_and_vector_from_graph

data = "scratch/02-12-NKI-ac0bc77-3"
x = get_graph_files(data, "desikan")

#%%
import os, sys, re
import numpy as np, networkx as nx

#%%
def get_graph_files(ndmg_participant_dir, atlas):
    """
    ndmg_participant_dir  : ndmg participant-level analysis output directory.
    atlas  : which atlas should you get the graph for?
    Returns: list of folder locations for all graph outputs
    """
    d = os.path.abspath(ndmg_participant_dir)  # to make things easier
    out = [
        os.path.join(
            directory, filename
        )  # Returns list of absolute path files in ndmg_participant_dir that end in '_adj.csv'.
        for directory, _, filenames in os.walk(d)
        for filename in filenames
        if (filename.endswith("_adj.csv") and atlas in filename)
    ]
    return out


#%%
def numpy_from_output_graph(input_csv_file):
    """ 
    Input: location of the .csv file for a single ndmg graph output
    Returns: numpy array from that .csv file
    """
    print(input_csv_file)


numpy_from_output_graph(x[0])

#%%
def matrix_and_vector_from_graph():
    """ 
    Input: List of graph output locations
    Returns: the tuple (matrix, target_vector).
    """
    pass


#%%
def main():
    data = "scratch/02-12-NKI-ac0bc77-3"
    # TODO: input participant dir, output matrix_and_vector_from_graph() csv files
    # TODO: write assertion tests. Do they normally go here? no idea. Putting them here for now.
    assert all(
        [os.path.exists(filename) for filename in get_graph_files(data, "desikan")]
    )  # Everything in output for get_graph_files is a real path
    data = "scratch/02-12-NKI-ac0bc77-3"
    x = get_graph_files(data, "desikan")
    print(x)


if __name__ == "__main__":
    main()
