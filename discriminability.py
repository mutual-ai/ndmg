""" 
Discriminability code. Takes in output of ndmg participant-level analysis.
"""
#%%
import os
import sys

#%%
def get_graph_files(ndmg_participant_dir):
    """
    Input: ndmg participant-level analysis output directory.
    Returns: folder locations for all graph outputs
    """
    pass


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
    data = 'scratch/02-12-NKI-ac0bc77-3'
    get_graph_files(data)

if __name__ == "__main__":
    main()