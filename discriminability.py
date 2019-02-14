""" 
Discriminability code. Takes in output of ndmg participant-level analysis.
Currently in the root directory for safekeeping, will be moved to a better home once it's done
"""

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
        if (
            filename.endswith("_adj.csv") and atlas in filename
        )  # Soft check on filenames. Will break if filename has 'atlas' and '_adj.csv' in it but is not the adjacency matrix for that atlas.
    ]
    return out


#%%


def numpy_from_output_graph(input_csv_file):
    """ 
    Input: location of the .csv file for a single ndmg graph output
    Returns: Vectorized numpy matrix from that .csv file
    """
    # convert input from csv file to numpy matrix, then return
    out = nx.read_weighted_edgelist(input_csv_file, delimiter=",")
    out = nx.to_numpy_matrix(out)
    return np.array(out)


#%%
def matrix_and_vector_from_graphs(ndmg_participant_dir, atlas):
    # TODO: Figure out if there's a more computationally efficient way than building from a loop, that still absolutely guarentees that the target vector and corresponding matrix row are from the same subject
    """ 
    The main worker function. Big loop. Each loop iteration adds a row to out_matrix, and adds the subject name to out_target_vector.
    
    --------------
    Input: List of graph output locations
    Returns: the tuple (out_matrix, out_target_vector).
    """
    out_matrix = np.empty((1, 70 * 70))  # TODO: make this dynamic to the atlas
    out_target_vector = []
    graphs = get_graph_files(ndmg_participant_dir, atlas)
    rgx = re.compile(
        r"(sub-)([a-zA-Z0-9]*)"
    )  # to be used for grabbing the subject name
    for filename in graphs:  # main loop we care about
        mat = numpy_from_output_graph(filename)  # make a numpy array
        if mat.shape == (
            70,
            70,
        ):  # TODO: make this dynamic to the atlas, currently it's only for desikan
            sub_and_session = "".join(rgx.search(filename).groups())
            out_target_vector.append(sub_and_session)  # update out_target_vector
            out_matrix = np.append(
                out_matrix, mat.flatten()[np.newaxis, :], axis=0
            )  # This is gross but I don't currently know a better way to do it. Will also leave the first row as the remnants of np.empty()...
    return (out_matrix[1:, :], out_target_vector)


#%%
def main():
    data = "scratch/02-12-NKI-ac0bc77-3"
    # TODO: input participant dir, output matrix_and_vector_from_graph() csv files
    # TODO: write assertion tests. Not sure if they normally go here.
    X, y = matrix_and_vector_from_graphs(
        data, "desikan"
    )  # just sticking this in a main function as a wrapper currently, will add functionality later
    np.savetxt("{}_X.csv".format(data), X, fmt="%f", delimiter=",")  # save x csv

    for i in y:  # make Y vector csv
        with open("{}_y.csv".format(data), "a") as f:
            f.write(i + "\n")


if __name__ == "__main__":
    main()
