import os
import numpy as np
import random
import pandas as pd
import re
import math
from PIL import Image, ImageDraw, ImageOps
import cv2

from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler

# PyTorch
import torch
import torch.nn as nn
import torch.utils.data as data
import torchvision.transforms as transforms
from torchvision.utils import save_image

from data.transforms.random_erasing import RandomErasing
from data.transforms.tps_transform import TPSTransform
from utils import set_random_seed, numerical_sort

IMG_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif',
    '.JPG', '.JPEG', '.PNG', '.PPM', '.BMP', '.PGM', '.TIF',
)

class NoizeDataset(data.Dataset):
    def __init__(self, args, root_dir, datamode = "train", z_dims = 512, image_height = 128, image_width = 128, train_progress_max = 8, data_augument = False, debug = False ):
        super(NoizeDataset, self).__init__()
        self.args = args
        self.datamode = datamode
        self.data_augument = data_augument
        self.image_height = image_height
        self.image_width = image_width
        self.train_progress_max = train_progress_max
        self.z_dims = z_dims
        self.train_progress = 0
        self.debug = debug

        self.noize_sizes_h = []
        self.noize_sizes_w = []
        for i in range(train_progress_max+1):
            self.noize_sizes_h.append(2**(i+2))
            self.noize_sizes_w.append(2**(i+2))

        self.image_t_dir = os.path.join( root_dir, "image_t" )
        self.image_t_names = sorted( [f for f in os.listdir(self.image_t_dir) if f.endswith(IMG_EXTENSIONS)], key=numerical_sort )

        # transform
        if( data_augument ):
            self.transform = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.LANCZOS ),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomAffine( degrees = (-10,10),  translate=(0.0, 0.0), scale = (1.00,1.00), resample=Image.BICUBIC ),
                    transforms.RandomPerspective(),
                    transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                    transforms.ToTensor(),
                    transforms.Normalize( [0.5,0.5,0.5], [0.5,0.5,0.5] ),
                    RandomErasing( probability = 0.5, sl = 0.02, sh = 0.2, r1 = 0.3, mean=[0.5, 0.5, 0.5] ),
                ]
            )

            self.transform_mask = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.NEAREST ),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomAffine( degrees = (-10,10),  translate=(0.0, 0.0), scale = (1.00,1.00), resample=Image.NEAREST ),
                    transforms.RandomPerspective(),
                    transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                    transforms.ToTensor(),
                    transforms.Normalize( [0.5], [0.5] ),
                    RandomErasing( probability = 0.5, sl = 0.02, sh = 0.2, r1 = 0.3, mean=[0.5, 0.5, 0.5] ),
                ]
            )

            self.transform_mask_woToTensor = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.NEAREST ),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomAffine( degrees = (-10,10),  translate=(0.0, 0.0), scale = (1.00,1.00), resample=Image.NEAREST ),
                    transforms.RandomPerspective(),
                    transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                    RandomErasing( probability = 0.5, sl = 0.02, sh = 0.2, r1 = 0.3, mean=[0.5, 0.5, 0.5] ),
                ]
            )
        else:
            self.transform = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.LANCZOS ),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                    transforms.ToTensor(),
                    transforms.Normalize( [0.5,0.5,0.5], [0.5,0.5,0.5] ),
                ]
            )
            self.transform_mask = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.NEAREST ),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                    transforms.ToTensor(),
#                    transforms.Normalize( [0.5], [0.5] ),
                    transforms.Normalize( [0.5,0.5,0.5], [0.5,0.5,0.5] ),
                ]
            )
            self.transform_mask_woToTensor = transforms.Compose(
                [
                    transforms.Resize( (args.image_height, args.image_width), interpolation=Image.NEAREST ),
                    transforms.CenterCrop( size = (args.image_height, args.image_width) ),
                ]
            )

        if( self.debug ):
            print( "self.image_t_dir :", self.image_t_dir)
            print( "len(self.image_t_names) :", len(self.image_t_names))
            print( "self.image_t_names[0:5] :", self.image_t_names[0:5])

        return

    def __len__(self):
        return len(self.image_t_names)

    def get_latent_z(self, z_dims, noize_type = "uniform" ):
        if( noize_type == "uniform" ):
            latent_z = torch.randn([z_dims])
        else:
            NotImplementedError()

        return latent_z

    def get_noize_map(self, c, h, w , noize_type = "uniform" ):
        if( noize_type == "uniform" ):
            noize_map = torch.randn([1,h,w])
        else:
            NotImplementedError()

        # チャネル次元は同じ値にする
        noize_map = noize_map.expand(c,h,w)

        # zero padding で境界をゼロ埋め
        pass

        return noize_map

    def __getitem__(self, index):
        image_t_name = self.image_t_names[index]
        self.seed_da = random.randint(0,10000)

        #--------------------------------
        # 入力ノイズ z （潜在空間 x）
        #--------------------------------
        latent_z = self.get_latent_z(self.z_dims)

        #--------------------------------
        # 入力ノイズマップ
        #--------------------------------
        noize_map_list = []
        for train_progress in range(self.train_progress_max):
            noize_h = self.noize_sizes_h[train_progress]
            noize_w = self.noize_sizes_w[train_progress]

            # input noize
            noize_map = self.get_noize_map(c=1, h=noize_h, w=noize_w)
            noize_map_list.append(noize_map)

        #---------------------
        # image_t
        #---------------------
        if( self.datamode == "train" ):
            image_t_list = []
            for train_progress in range(self.train_progress_max):
                noize_h = self.noize_sizes_h[train_progress]
                noize_w = self.noize_sizes_w[train_progress]

                # transform
                self.transform = transforms.Compose(
                    [
                        transforms.Resize( (noize_h, noize_w), interpolation=Image.LANCZOS ),
                        transforms.CenterCrop( size = (noize_h, noize_w) ),
                        transforms.ToTensor(),
                        transforms.Normalize( [0.5,0.5,0.5], [0.5,0.5,0.5] ),
                    ]
                )

                # image
                image_t = Image.open( os.path.join(self.image_t_dir, image_t_name) ).convert('RGB')
                image_t = self.transform(image_t)
                image_t_list.append(image_t)

        #---------------------
        # returns
        #---------------------
        if( self.datamode == "train" ):
            results_dict = {
                "latent_z" : latent_z,
                "noize_map_list" : noize_map_list,
                "image_t_name" : image_t_name,
                "image_t_list" : image_t_list,
            }
        else:
            results_dict = {
                "latent_z" : latent_z,
            }

        return results_dict

