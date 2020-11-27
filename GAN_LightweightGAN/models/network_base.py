# -*- coding:utf-8 -*-
import os
import numpy as np
import functools

import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.nn.utils import spectral_norm
import torchvision


class Reshape(nn.Module):
    def __init__(self, h, w):
        super(Reshape, self).__init__()
        self.h = h
        self.w = w
        return

    def forward(self, input):
        output = input.view( input.shape[0], -1, self.h, self.w)
        return output

    def __repr__(self):
        return self.__class__.__name__ + '-> h={}, w={}'.format(self.h, self.w)


class GLU(nn.Module):
    """
    GLU 活性化関数 / GLU(a,b) = a ⊗ sigmoid(b)
    """
    def __init__(self, split_dim=1):
        """
        [args]
            split_dim : <int> dimension on which to split the input
        """
        super(GLU, self).__init__()
        self.split_dim = split_dim
        return

    def forward(self, input ):
        return F.glu(input, self.split_dim)
