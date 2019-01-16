#!/usr/bin/env python

# Copyright 2016 NeuroData (http://neurodata.io)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# graph.py
# Created by Greg Kiar on 2016-01-27.
# Email: gkiar@jhu.edu

from __future__ import print_function

from itertools import product
from collections import defaultdict
import numpy as np
import networkx as nx
import nibabel as nb
import ndmg
import time


class graph(object):
    def __init__(self, N, rois, attr=None, sens="dwi"):
        """
        Initializes the graph with nodes corresponding to the number of ROIs

        **Positional Arguments:**

                N:
                    - Number of rois
                rois:
                    - Set of ROIs as either an array or niftii file)
                attr:
                    - Node or graph attributes. Can be a list. If 1 dimensional
                      will be interpretted as a graph attribute. If N
                      dimensional will be interpretted as node attributes. If
                      it is any other dimensional, it will be ignored.
        """
        self.N = N
        self.edge_dict = defaultdict(int)

        self.rois = nb.load(rois).get_data()
        n_ids = np.unique(self.rois)
        self.n_ids = n_ids[n_ids > 0]

        self.modal = sens
        pass

    def make_graph(self, streamlines, attr=None):
        """
        Takes streamlines and produces a graph

        **Positional Arguments:**

                streamlines:
                    - Fiber streamlines either file or array in a dipy EuDX
                      or compatible format.
        """
        self.g = nx.Graph(name="Generated by NeuroData's MRI Graphs (ndmg)",
                          version=ndmg.version,
                          date=time.asctime(time.localtime()),
                          source="http://m2g.io",
                          region="brain",
                          sensor=self.modal,
                          ecount=0,
                          vcount=len(self.n_ids)
                          )
        print(self.g.graph)
        [str(self.g.add_node(ids)) for ids in self.n_ids]

        nlines = np.shape(streamlines)[0]
        print("# of Streamlines: " + str(nlines))
        print_id = np.max((int(nlines*0.05), 1))  # in case nlines*.05=0
        for idx, streamline in enumerate(streamlines):
            if (idx % print_id) == 0:
                print(idx)

            points = np.round(streamline).astype(int)
            p = set()
            for point in points:
                try:
                    loc = self.rois[point[0], point[1], point[2]]
                except IndexError:
                    pass
                else:
                    pass

                if loc:
                    p.add(loc)
            edges = set([tuple(sorted(x)) for x in product(p, p)])
            for edge in edges:
                lst = tuple(sorted([str(node) for node in edge]))
                self.edge_dict[lst] += 1
        edge_list = [(int(k[0]), int(k[1]), v) for k, v in self.edge_dict.items()]
        self.g.add_weighted_edges_from(edge_list)

    def cor_graph(self, timeseries, attr=None):
        """
        Takes timeseries and produces a correlation matrix

        **Positional Arguments:**
            timeseries:
                -the timeseries file to extract correlation for.
                          dimensions are [numrois]x[numtimesteps]
        """
        ts = timeseries[0]
        rois = timeseries[1]
        print("Estimating correlation matrix for {} ROIs...".format(self.N))
        self.g = np.abs(np.corrcoef(ts))  # calculate pearson correlation
        self.g = np.nan_to_num(self.g).astype(object)
        self.n_ids = rois
        # roilist = self.g.nodes()

        # for (idx_out, roi_out) in enumerate(roilist):
        #     for (idx_in, roi_in) in enumerate(roilist):
        #         self.edge_dict[(roi_out, roi_in)] = float(cor[idx_out, idx_in])

        # edge_list = [(str(k[0]), str(k[1]), v) for k, v in self.edge_dict.items()]
        # self.g.add_weighted_edges_from(edge_list)
        return self.g        

    def get_graph(self):
        """
        Returns the graph object created
        """
        try:
            return self.g
        except AttributeError:
            print("Error: the graph has not yet been defined.")
            pass

    def as_matrix(self):
        """
        Returns the graph as a matrix.
        """
        g = self.get_graph()
        return nx.to_numpy_matrix(g, nodelist=np.sort(g.nodes()).tolist())

    def save_graph(self, graphname):
        """
        Saves the graph to disk

        **Positional Arguments:**

                graphname:
                    - Filename for the graph
        """
        if self.modal == 'dwi':
            self.g.graph['ecount'] = nx.number_of_edges(self.g)
            nx.write_weighted_edgelist(self.g, graphname, delimiter=",")

        elif self.modal == 'func':
            np.savetxt(graphname, self.g, comments='', delimiter=',',
                header=','.join([str(n) for n in self.n_ids]))
        else:
            raise ValueError("Unsupported Modality.")
        pass

    def summary(self):
        """
        User friendly wrapping and display of graph properties
        """
        print("\n Graph Summary:")
        print(nx.info(self.g))
        pass
