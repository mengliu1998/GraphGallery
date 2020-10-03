import tensorflow as tf


from graphgallery.nn.models import SemiSupervisedModel
from graphgallery.sequence import FullBatchNodeSequence
from graphgallery.utils.decorators import EqualVarLength

from graphgallery.nn.models.semisupervised.tf_models.dagnn import DAGNN as tfDAGNN

from graphgallery import transforms as T


class DAGNN(SemiSupervisedModel):
    """
        Implementation of Deep Adaptive Graph Neural Network (DAGNN). 
        `Towards Deeper Graph Neural Networks <https://arxiv.org/abs/2007.09296>`
        Pytorch implementation: <https://github.com/mengliu1998/DeeperGNN>
    """

    def __init__(self, graph, K=10, adj_transform="normalize_adj", attr_transform=None,
                 device='cpu:0', seed=None, name=None, **kwargs):
        """Create a Deep Adaptive Graph Neural Network (DAGNN) model.

        This can be instantiated in several ways:

            model = DAGNN(graph)
                with a `graphgallery.data.Graph` instance representing
                A sparse, attributed, labeled graph.

            model = DAGNN(adj_matrix, attr_matrix, labels)
                where `adj_matrix` is a 2D Scipy sparse matrix denoting the graph,
                 `attr_matrix` is a 2D Numpy array-like matrix denoting the node 
                 attributes, `labels` is a 1D Numpy array denoting the node labels.


        Parameters:
        ----------
        graph: An instance of `graphgallery.data.Graph` or a tuple (list) of inputs.
            A sparse, attributed, labeled graph.
        K: integer. optional
            propagation steps of adjacency matrix.
            (default :obj: `10`)
        adj_transform: string, `transform`, or None. optional
            How to transform the adjacency matrix. See `graphgallery.transforms`
            (default: :obj:`'normalize_adj'` with normalize rate `-0.5`.
            i.e., math:: \hat{A} = D^{-\frac{1}{2}} A D^{-\frac{1}{2}}) 
        attr_transform: string, `transform`, or None. optional
            How to transform the node attribute matrix. See `graphgallery.transforms`
            (default :obj: `None`)
        device: string. optional 
            The device where the model is running on. You can specified `CPU` or `GPU` 
            for the model. (default: :str: `CPU:0`, i.e., running on the 0-th `CPU`)
        seed: interger scalar. optional 
            Used in combination with `tf.random.set_seed` & `np.random.seed` 
            & `random.seed` to create a reproducible sequence of tensors across 
            multiple calls. (default :obj: `None`, i.e., using random seed)
        name: string. optional
            Specified name for the model. (default: :str: `class.__name__`)
        kwargs: other customized keyword Parameters.

        """
        super().__init__(graph, device=device, seed=seed, name=name, **kwargs)

        self.K = K
        self.adj_transform = T.get(adj_transform)
        self.attr_transform = T.get(attr_transform)
        self.process()

    def process_step(self):
        graph = self.graph
        adj_matrix = self.adj_transform(graph.adj_matrix)
        attr_matrix = self.attr_transform(graph.attr_matrix)

        self.feature_inputs, self.structure_inputs = T.astensors(
            attr_matrix, adj_matrix, device=self.device)

    # use decorator to make sure all list arguments have the same length
    @EqualVarLength()
    def build(self, hiddens=[64], activations=['relu'], dropout=0.5, l2_norm=5e-3,
              lr=0.01, use_bias=False):

        if self.kind == "T":
            with tf.device(self.device):
                self.model = tfDAGNN(self.graph.n_attrs, self.graph.n_classes,
                                        hiddens=hiddens,
                                        activations=activations,
                                        dropout=dropout, l2_norm=l2_norm,
                                        lr=lr, use_bias=use_bias, K=self.K)
        else:
            raise NotImplementedError

    def train_sequence(self, index):
        
        labels = self.graph.labels[index]
        sequence = FullBatchNodeSequence(
            [self.feature_inputs, self.structure_inputs, index], labels, device=self.device)
        return sequence