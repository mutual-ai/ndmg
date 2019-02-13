""" 
Discriminability code. Takes in output of ndmg participant-level analysis.
"""

# TODO: write tests for each of these


#%%
import os, sys, re

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


data = "scratch/02-12-NKI-ac0bc77-3"
x = get_graph_files(data, "desikan")
x

#%%
def numpy_from_graph():
    """ 
    Input: location of the .csv file for a single ndmg graph output
    Returns: numpy array from that .csv file
    """
    pass


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
        [os.path.exists(filename) for filename in get_graph_files(data)]
    )  # Everything in output for get_graph_files is a real path
    pass


if __name__ == "__main__":
    main()
