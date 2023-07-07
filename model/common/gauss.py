import torch.nn as nn
import torch
from typing import List
from utils.utils import initialize_weights


class Gaussian_Density_Model(nn.Module):
    """
    implementation of a single Gaussian Density model. The model is inherently bivariate
    (produces mixtures of Gaussian distributions over 2D space).
    """

    def __init__(self, input_dim: int, hidden_dims: List[int], activation: str = "relu"):
        super().__init__()
        assert activation in ("tanh", "sigmoid", "relu"), ValueError(f"activation type unknown: {activation}")

        self.activation = getattr(torch, activation)  # default: torch.relu

        layer_dims = [input_dim, *hidden_dims]

        self.affine_layers = nn.ModuleList()
        for in_dim, out_dim in zip(layer_dims[:-1], layer_dims[1:]):
            self.affine_layers.append(nn.Linear(in_dim, out_dim))

        self.layer_mu = nn.Linear(layer_dims[-1], 2)
        self.layer_sig = nn.Linear(layer_dims[-1], 2)
        self.layer_rho = nn.Linear(layer_dims[-1], 1)

        initialize_weights(self.affine_layers.modules())
        initialize_weights(self.layer_mu.modules())
        initialize_weights(self.layer_sig.modules())
        initialize_weights(self.layer_rho.modules())

    def forward(self, x):
        for affine in self.affine_layers:
            x = self.activation(affine(x))

        # once we have reached the last hidden layer, we connect it to each of the individual layers
        # responsible for modelling different parameters
        mu = self.layer_mu(x)
        sig = torch.exp(self.layer_sig(x))      # strictly positive
        rho = torch.tanh(self.layer_rho(x))     # within (-1, 1)
        return mu, sig, rho


if __name__ == '__main__':

    from torch.distributions import MultivariateNormal
    from tqdm import tqdm
    from model.agentformer_loss import gaussian_twodee_nll, gaussian_twodee_nll_2

    dist_params = {
        "mu": [0., 0.],
        "sig": [1., 1.],
        "rho": 0.0
    }
    tensor_shape = [30, 12]  # epochs, batches, datablobs...
    model_input_dim = 256
    model_hidden_dims = [128, 64]
    model_activation = "relu"
    n_training_steps = 1000
    nll_loss = gaussian_twodee_nll_2  # [gaussian_twodee_nll, gaussian_twodee_nll_2]

    gt_mu = torch.tensor(dist_params["mu"], dtype=torch.float64)
    gt_Sig = torch.tensor(
        [[dist_params["sig"][0] ** 2, dist_params["rho"] * dist_params["sig"][0] * dist_params["sig"][1]],
         [dist_params["rho"] * dist_params["sig"][0] * dist_params["sig"][1], dist_params["sig"][1] ** 2]],
        dtype=torch.float64)

    print(f"{gt_mu=}")
    print(f"{gt_Sig=}")

    distrib = MultivariateNormal(loc=gt_mu, covariance_matrix=gt_Sig)

    gauss = Gaussian_Density_Model(
        input_dim=model_input_dim, hidden_dims=model_hidden_dims, activation=model_activation
    )
    optimizer = torch.optim.Adam(gauss.parameters())

    for i in tqdm(range(n_training_steps)):
        gauss.zero_grad()
        optimizer.zero_grad()

        y = distrib.sample(sample_shape=tensor_shape)
        x = torch.randn([*tensor_shape, model_input_dim])

        mu, sig, rho = gauss(x)
        loss = nll_loss(mu, sig, rho, y)

        loss.backward()

        optimizer.step()

        assert torch.all(sig >= 0.0)
        assert torch.all(-1.0 <= rho) and torch.all(rho <= 1.0)

    print("\"True\" Distribution parameters:")
    [print(f"{k}: {v}") for k, v in dist_params.items()]

    print("Mean of Generated distributions:")
    x = torch.randn([*tensor_shape, 256])
    mu, sig, rho = gauss(x)
    print(f"{torch.mean(mu[..., 0])=}")
    print(f"{torch.mean(mu[..., 1])=}")
    print(f"{torch.mean(sig[..., 0])=}")
    print(f"{torch.mean(sig[..., 1])=}")
    print(f"{torch.mean(rho[..., 0])=}")